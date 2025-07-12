#!/usr/bin/env python3
"""
Test file with intentional SOLID principle violations to test hook blocking
"""

class GodClass:
    """This class violates Single Responsibility Principle"""
    
    def __init__(self):
        # Direct instantiation violates Dependency Inversion Principle
        self.database = DatabaseConnection()
        self.api_client = APIClient()
        self.logger = LoggingService()
        self.cache = CacheManager()
        self.validator = DataValidator()
        self.formatter = OutputFormatter()
    
    def get_user_data(self, user_id):
        """Data access responsibility"""
        return self.database.query(f"SELECT * FROM users WHERE id = {user_id}")
    
    def save_user_data(self, user_data):
        """Persistence responsibility"""
        self.database.execute(f"INSERT INTO users VALUES {user_data}")
    
    def validate_user_data(self, user_data):
        """Validation responsibility"""
        return self.validator.validate(user_data)
    
    def format_user_output(self, user_data):
        """Presentation responsibility"""
        return self.formatter.format(user_data)
    
    def send_user_notification(self, user_id, message):
        """Communication responsibility"""
        user = self.get_user_data(user_id)
        self.api_client.send_email(user['email'], message)
    
    def calculate_user_score(self, user_data):
        """Business logic responsibility"""
        score = 0
        if user_data['posts'] > 100:
            score += 50
        if user_data['comments'] > 500:
            score += 30
        if user_data['likes'] > 1000:
            score += 20
        return score
    
    def process_user(self, user_id):
        """Method with too many lines - violates SRP"""
        # Get user data
        user_data = self.get_user_data(user_id)
        
        # Validate
        if not self.validate_user_data(user_data):
            raise ValueError("Invalid user data")
        
        # Calculate score
        score = self.calculate_user_score(user_data)
        
        # Update user
        user_data['score'] = score
        self.save_user_data(user_data)
        
        # Format for output
        formatted = self.format_user_output(user_data)
        
        # Send notification
        self.send_user_notification(user_id, f"Your score is {score}")
        
        # Log the operation
        self.logger.log(f"Processed user {user_id}")
        
        # Cache the result
        self.cache.set(f"user_{user_id}", formatted)
        
        # More processing...
        if score > 80:
            self.send_user_notification(user_id, "You're a power user!")
        elif score > 50:
            self.send_user_notification(user_id, "Keep it up!")
        else:
            self.send_user_notification(user_id, "Try to be more active!")
        
        return formatted


class ChildClassBad(GodClass):
    """Violates Liskov Substitution Principle"""
    
    def get_user_data(self, user_id):
        """This breaks the parent contract by raising NotImplementedError"""
        raise NotImplementedError("We don't support this anymore")


# Dummy classes to make the code syntactically valid
class DatabaseConnection:
    def query(self, sql): pass
    def execute(self, sql): pass

class APIClient:
    def send_email(self, email, message): pass

class LoggingService:
    def log(self, message): pass

class CacheManager:
    def set(self, key, value): pass

class DataValidator:
    def validate(self, data): return True

class OutputFormatter:
    def format(self, data): return str(data)