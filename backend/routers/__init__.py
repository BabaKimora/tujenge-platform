"""
Tujenge Platform - Router Imports
Centralized router imports for the FastAPI application
"""

# Import existing routers
from . import customers

# Create placeholder routers for missing modules to prevent import errors
class PlaceholderRouter:
    """Placeholder router to prevent import errors"""
    def __init__(self, name):
        self.name = name
        from fastapi import APIRouter
        self.router = APIRouter()
        self.router.get(f"/{name}")(lambda: {"message": f"{name.title()} endpoint - to be implemented"})

# Create placeholder modules for missing routers
import types

# Auth router placeholder
auth = types.ModuleType('auth')
auth.router = PlaceholderRouter('auth').router

# Other placeholder routers
loans = types.ModuleType('loans')
loans.router = PlaceholderRouter('loans').router

transactions = types.ModuleType('transactions')
transactions.router = PlaceholderRouter('transactions').router

mobile_money = types.ModuleType('mobile_money')
mobile_money.router = PlaceholderRouter('mobile-money').router

government = types.ModuleType('government')
government.router = PlaceholderRouter('government').router

documents = types.ModuleType('documents')
documents.router = PlaceholderRouter('documents').router

users = types.ModuleType('users')
users.router = PlaceholderRouter('users').router

branches = types.ModuleType('branches')
branches.router = PlaceholderRouter('branches').router

regions = types.ModuleType('regions')
regions.router = PlaceholderRouter('regions').router

analytics = types.ModuleType('analytics')
analytics.router = PlaceholderRouter('analytics').router

health = types.ModuleType('health')
health.router = PlaceholderRouter('health').router

admin = types.ModuleType('admin')
admin.router = PlaceholderRouter('admin').router 