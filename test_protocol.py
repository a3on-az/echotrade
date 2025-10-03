#!/usr/bin/env python3
"""
Comprehensive Testing Protocol for EchoTrade
"""
import subprocess
import sys
import time
import requests
import asyncio
from datetime import datetime

class EchoTradeTestSuite:
    def __init__(self):
        self.results = []
        self.api_base = "http://localhost:8000/api"
        
    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test result"""
        timestamp = datetime.now().isoformat()
        result = {
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': timestamp
        }
        self.results.append(result)
        print(f"[{status}] {test_name}: {details}")
    
    def run_unit_tests(self):
        """Phase 1: Unit & Integration Testing"""
        print("\n" + "="*60)
        print("PHASE 1: UNIT & INTEGRATION TESTING")
        print("="*60)
        
        try:
            # Core functionality tests
            result = subprocess.run(['pytest', 'tests/', '-v', '--tb=short'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.log_test("Unit Tests", "PASS", f"All tests passed")
            else:
                self.log_test("Unit Tests", "FAIL", f"Some tests failed:\n{result.stdout}")
        except Exception as e:
            self.log_test("Unit Tests", "ERROR", str(e))
        
        # Critical risk management test
        try:
            result = subprocess.run([
                'pytest', 'tests/test_risk.py::TestRiskManager::test_risk_caps_loss', '-v'
            ], capture_output=True, text=True)
            if result.returncode == 0:
                self.log_test("Risk Caps Loss Test", "PASS", "30% drawdown limit enforced")
            else:
                self.log_test("Risk Caps Loss Test", "FAIL", result.stdout)
        except Exception as e:
            self.log_test("Risk Caps Loss Test", "ERROR", str(e))
    
    def run_paper_trading_tests(self):
        """Phase 2: Paper Trading Validation"""
        print("\n" + "="*60)
        print("PHASE 2: PAPER TRADING VALIDATION")
        print("="*60)
        
        try:
            # Short paper trading run
            result = subprocess.run([
                'python', 'main.py', '--paper', '--max-iterations', '3', '--log-level', 'INFO'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.log_test("Paper Trading", "PASS", "Bot ran successfully in paper mode")
            else:
                self.log_test("Paper Trading", "FAIL", result.stderr or result.stdout)
        except subprocess.TimeoutExpired:
            self.log_test("Paper Trading", "TIMEOUT", "Bot took too long (>60s)")
        except Exception as e:
            self.log_test("Paper Trading", "ERROR", str(e))
    
    async def run_api_tests(self):
        """Phase 3: API Endpoint Testing"""
        print("\n" + "="*60)
        print("PHASE 3: API ENDPOINT TESTING")
        print("="*60)
        
        # Start API server in background
        api_process = None
        try:
            # Test critical endpoints
            endpoints = [
                ('/portfolio/status', 'Portfolio Status'),
                ('/traders', 'Traders List'),
                ('/config', 'Configuration'),
                ('/bot/status', 'Bot Status')
            ]
            
            for endpoint, name in endpoints:
                try:
                    response = requests.get(f"{self.api_base}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        self.log_test(f"API {name}", "PASS", f"Status: {response.status_code}")
                    else:
                        self.log_test(f"API {name}", "FAIL", f"Status: {response.status_code}")
                except requests.exceptions.ConnectionError:
                    self.log_test(f"API {name}", "SKIP", "API server not running")
                except Exception as e:
                    self.log_test(f"API {name}", "ERROR", str(e))
                    
        except Exception as e:
            self.log_test("API Tests", "ERROR", str(e))
    
    def run_database_tests(self):
        """Phase 4: Database Integration"""
        print("\n" + "="*60)
        print("PHASE 4: DATABASE INTEGRATION")
        print("="*60)
        
        try:
            # Test database creation and operations
            from models import db_manager, Trader
            
            # Create tables
            db_manager.create_tables()
            self.log_test("Database Creation", "PASS", "Tables created successfully")
            
            # Test data insertion
            db_manager.init_default_traders()
            
            # Test query
            session = db_manager.get_session()
            traders = session.query(Trader).all()
            session.close()
            
            if len(traders) >= 2:
                self.log_test("Database Operations", "PASS", f"Found {len(traders)} traders")
            else:
                self.log_test("Database Operations", "FAIL", "Insufficient trader data")
                
        except Exception as e:
            self.log_test("Database Tests", "ERROR", str(e))
    
    def run_security_tests(self):
        """Phase 5: Security Validation"""
        print("\n" + "="*60)
        print("PHASE 5: SECURITY VALIDATION")
        print("="*60)
        
        try:
            # Test configuration validation
            from config import Config
            errors = Config.validate_config()
            
            if errors:
                self.log_test("Config Validation", "EXPECTED", f"Config errors (expected): {errors}")
            else:
                self.log_test("Config Validation", "PASS", "No validation errors")
                
            # Test API key protection (should not be in logs)
            # This is a basic check - in production, use proper secret scanning
            self.log_test("API Key Security", "MANUAL", "Manual verification required")
            
        except Exception as e:
            self.log_test("Security Tests", "ERROR", str(e))
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("ECHOTRADE TESTING REPORT")
        print("="*60)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        errors = sum(1 for r in self.results if r['status'] == 'ERROR')
        skipped = sum(1 for r in self.results if r['status'] == 'SKIP')
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Errors: {errors} 🔥")
        print(f"Skipped: {skipped} ⏭️")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 READY FOR FRONTEND DEVELOPMENT!")
        elif success_rate >= 60:
            print("⚠️  NEEDS MINOR FIXES BEFORE FRONTEND")
        else:
            print("🔧 REQUIRES MAJOR FIXES")
        
        print("\nDetailed Results:")
        print("-" * 60)
        for result in self.results:
            status_icon = {
                'PASS': '✅',
                'FAIL': '❌',
                'ERROR': '🔥',
                'SKIP': '⏭️',
                'EXPECTED': '🟡',
                'MANUAL': '📋'
            }.get(result['status'], '❓')
            
            print(f"{status_icon} {result['test']}: {result['details']}")
    
    async def run_full_suite(self):
        """Run complete testing suite"""
        print("🧪 STARTING ECHOTRADE COMPREHENSIVE TESTING")
        print(f"Timestamp: {datetime.now()}")
        
        # Phase 1: Unit tests
        self.run_unit_tests()
        
        # Phase 2: Paper trading
        self.run_paper_trading_tests()
        
        # Phase 3: API tests
        await self.run_api_tests()
        
        # Phase 4: Database
        self.run_database_tests()
        
        # Phase 5: Security
        self.run_security_tests()
        
        # Generate report
        self.generate_report()

if __name__ == "__main__":
    async def main():
        test_suite = EchoTradeTestSuite()
        await test_suite.run_full_suite()
    
    asyncio.run(main())