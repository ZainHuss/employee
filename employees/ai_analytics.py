import pandas as pd
import numpy as np
from django.db import models
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from sklearn.pipeline import Pipeline
from .models import Employee, Attendance, EmployeePrediction, PerformanceReview, Department
from django.db.models import Avg, Count, Q, F, FloatField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import joblib
import os
from django.conf import settings
from django.db.models import Case, When

MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'turnover_model.joblib')
SCALER_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'scaler.joblib')

class TurnoverPredictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.features = [
            'salary', 'performance', 'absences', 'years_at_company',
            'promotions', 'department_risk', 'tenure', 'recent_trend'
        ]
        self.target = 'left_company'
    
    def prepare_training_data(self):
        """Prepare comprehensive training data with advanced features"""
        # First get department risks
        dept_risks = {
            dept['id']: dept['risk']
            for dept in Department.objects.annotate(
                risk=Avg(
                    Case(
                        When(employee__is_active=False, then=1.0),
                        default=0.0,
                        output_field=FloatField()
                    )
                )
            ).values('id', 'risk')
        }

        # Get base employee queryset with annotations
        employees = Employee.objects.annotate(
            avg_performance=Avg('performance_reviews__rating'),
            absence_count=Count('attendance', filter=Q(attendance__status='absent')),
            promotion_count=Count('promotions')  # Assuming you have a Promotion model
        ).select_related('department').prefetch_related(
            'performance_reviews', 'attendance_set'
        ).filter(department__isnull=False)

        data = []
        for emp in employees:
            years_at_company = 0
            if emp.hire_date:
                delta = timezone.now().date() - emp.hire_date
                years_at_company = delta.days / 365
            
            # Calculate performance trend
            performances = list(emp.performance_reviews.order_by('-review_date').values_list('rating', flat=True)[:3])
            if len(performances) >= 2:
                trend = performances[0] - performances[1]  # Simple difference between last two scores
            else:
                trend = 0.0
            
            data.append({
                'salary': float(emp.salary),
                'performance': emp.avg_performance if emp.avg_performance else emp.performance_score,
                'absences': emp.absence_count,
                'years_at_company': years_at_company,
                'promotions': emp.promotion_count,
                'department_risk': dept_risks.get(emp.department.id, 0.0) if emp.department else 0.0,
                'tenure': years_at_company,
                'recent_trend': trend,
                'left_company': not emp.is_active
            })
        
        return pd.DataFrame(data)
    
    def prepare_features(self, employee):
        """Prepare feature vector for a single employee"""
        # Calculate years of experience
        years_exp = 0
        if employee.hire_date:
            delta = timezone.now().date() - employee.hire_date
            years_exp = delta.days / 365
        
        # Calculate department risk (average turnover in department)
        dept_risk = 0.0
        if employee.department:
            dept_risk = Employee.objects.filter(
                department=employee.department,
                is_active=False
            ).count() / max(1, Employee.objects.filter(department=employee.department).count())
        
        # Calculate performance trend
        trend = self.calculate_performance_trend(employee)
        
        # Get performance score (use average of reviews if available, else use base score)
        performance_score = employee.performance_reviews.aggregate(
            avg_score=Avg('rating')
        )['avg_score'] or employee.performance_score
        
        return np.array([[
            float(employee.salary),
            performance_score,
            employee.attendance_set.filter(status='absent').count(),
            years_exp,
            employee.promotions.count() if hasattr(employee, 'promotions') else 0,
            dept_risk,
            years_exp,  # Using years_exp as tenure since we don't have separate tenure field
            trend
        ]])
    
    def calculate_performance_trend(self, employee):
        """Calculate performance trend using last 3 reviews"""
        try:
            # Get performance data points
            performances = list(employee.performance_reviews.order_by('-review_date').values_list('rating', flat=True)[:3])
            
            if len(performances) >= 2:
                # Calculate slope of performance trend
                x = np.arange(len(performances))
                y = np.array(performances)
                trend = np.polyfit(x, y, 1)[0]
                return trend
            return 0.0
        except:
            return 0.0
    
    def handle_imbalanced_data(self, X, y):
        """Apply SMOTE to handle class imbalance"""
        smote = SMOTE(sampling_strategy='minority', random_state=42)
        X_res, y_res = smote.fit_resample(X, y)
        return X_res, y_res
    
    def train_model(self):
        """Train and optimize the turnover prediction model"""
        try:
            df = self.prepare_training_data()
            
            if len(df) < 20 or self.target not in df.columns:
                print("Insufficient data for training")
                return None
            
            # Clean and prepare data
            df = df.dropna()
            if len(df) < 10:
                print("Not enough data after cleaning")
                return None
            
            X = df[self.features]
            y = df[self.target]
            
            # Handle class imbalance
            X, y = self.handle_imbalanced_data(X, y)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, 
                test_size=0.2,
                random_state=42,
                stratify=y
            )
            
            # Create preprocessing and modeling pipeline
            pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('classifier', GradientBoostingClassifier(random_state=42))
            ])
            
            # Hyperparameter tuning
            param_grid = {
                'classifier__n_estimators': [100, 200],
                'classifier__learning_rate': [0.01, 0.1],
                'classifier__max_depth': [3, 5]
            }
            
            grid_search = GridSearchCV(
                pipeline,
                param_grid,
                cv=5,
                scoring='roc_auc',
                n_jobs=-1
            )
            
            grid_search.fit(X_train, y_train)
            
            # Get best model
            self.model = grid_search.best_estimator_
            self.scaler = self.model.named_steps['scaler']
            
            # Evaluate model
            y_pred = self.model.predict(X_test)
            y_proba = self.model.predict_proba(X_test)[:, 1]
            
            print("Best Parameters:", grid_search.best_params_)
            print(classification_report(y_test, y_pred))
            print("ROC AUC Score:", roc_auc_score(y_test, y_proba))
            
            # Save model and scaler
            self.save_model()
            
            return self.model
        
        except Exception as e:
            print(f"Error training model: {str(e)}")
            return None
    
    def save_model(self):
        """Save trained model and scaler to disk"""
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(self.model, MODEL_PATH)
        joblib.dump(self.scaler, SCALER_PATH)
    
    def load_model(self):
        """Load trained model from disk"""
        try:
            self.model = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            return True
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            return False
    
    def predict_risk(self, employee):
        """Predict turnover risk for a single employee"""
        try:
            if not self.model and not self.load_model():
                print("No trained model available")
                return 0.0
            
            features = self.prepare_features(employee)
            features_scaled = self.scaler.transform(features)
            
            risk = self.model.predict_proba(features_scaled)[0][1]
            return float(risk)
        
        except Exception as e:
            print(f"Prediction error: {str(e)}")
            return 0.0
    
    def generate_recommendation(self, employee, risk):
        """Generate personalized recommendation based on risk factors"""
        try:
            if not isinstance(risk, (int, float)):
                risk = 0.0
            
            recommendations = []
            
            # Get employee stats
            absence_count = employee.attendance_set.filter(status='absent').count()
            performance_reviews = employee.performance_reviews.order_by('-review_date')
            
            # High risk recommendations
            if risk > 0.75:
                recommendations.append(_("Immediate intervention required"))
                if employee.salary < (employee.department.avg_salary if hasattr(employee.department, 'avg_salary') else 0):
                    recommendations.append(_("Salary review recommended"))
                
                if absence_count > 3:
                    recommendations.append(_("Address attendance issues"))
            
            # Moderate risk
            elif risk > 0.55:
                recommendations.append(_("Development plan needed"))
                if performance_reviews.count() >= 2 and (performance_reviews[0].rating - performance_reviews[1].rating) < -0.5:
                    recommendations.append(_("Performance improvement plan"))
                else:
                    recommendations.append(_("Career development discussion"))
            
            # Low risk
            else:
                recommendations.append(_("Regular engagement activities"))
                if employee.hire_date and (timezone.now().date() - employee.hire_date).days > 5*365:
                    recommendations.append(_("Consider leadership opportunities"))
            
            # Add department-specific recommendations if available
            if hasattr(employee, 'department') and employee.department:
                dept_turnover = Employee.objects.filter(
                    department=employee.department,
                    is_active=False
                ).count() / max(1, Employee.objects.filter(department=employee.department).count())
                
                if dept_turnover > 0.3:  # 30% turnover rate
                    recommendations.append(_("Department retention strategy"))
            
            return " | ".join(recommendations) if recommendations else _("No specific recommendations")
        
        except Exception as e:
            print(f"Recommendation error: {str(e)}")
            return _("Recommendation engine error")

def update_all_predictions():
    """Update predictions for all active employees"""
    predictor = TurnoverPredictor()
    
    # Load or train model
    if not predictor.load_model():
        if not predictor.train_model():
            return False
    
    # Get active employees with related data
    active_employees = Employee.objects.filter(is_active=True).select_related(
        'department'
    ).prefetch_related(
        'attendance_set', 'performance_reviews'
    )
    
    batch_size = 50
    for i in range(0, active_employees.count(), batch_size):
        batch = active_employees[i:i+batch_size]
        predictions = []
        
        for emp in batch:
            risk = predictor.predict_risk(emp)
            trend = predictor.calculate_performance_trend(emp)
            recommendation = predictor.generate_recommendation(emp, risk)
            
            predictions.append(EmployeePrediction(
                employee=emp,
                turnover_risk=risk,
                performance_trend=trend,
                recommended_action=recommendation,
                prediction_date=timezone.now()
            ))
        
        # Bulk create or update predictions
        EmployeePrediction.objects.bulk_create(
            predictions,
            update_conflicts=True,
            update_fields=['turnover_risk', 'performance_trend', 'recommended_action', 'prediction_date'],
            unique_fields=['employee']
        )
    
    return True

def model_performance_report():
    """Generate a performance report for the current model"""
    predictor = TurnoverPredictor()
    df = predictor.prepare_training_data()
    
    if len(df) < 10:
        return {"error": "Insufficient data for evaluation"}
    
    X = df[predictor.features]
    y = df[predictor.target]
    
    if not predictor.load_model():
        return {"error": "No trained model available"}
    
    y_pred = predictor.model.predict(X)
    y_proba = predictor.model.predict_proba(X)[:, 1]
    
    report = classification_report(y, y_pred, output_dict=True)
    roc_auc = roc_auc_score(y, y_proba)
    
    return {
        "classification_report": report,
        "roc_auc": roc_auc,
        "feature_importance": dict(zip(
            predictor.features,
            predictor.model.named_steps['classifier'].feature_importances_
        )),
        "model_type": str(predictor.model.named_steps['classifier'].__class__.__name__)
    }