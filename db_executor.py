#!/usr/bin/env python3
"""
Database Execution Module (DEM)

This module executes AI-generated SQL statements against the connected database
and formats the results for display in the frontend.

Key Responsibilities:
1. Execute validated SQL statements safely
2. Handle transactions and rollbacks
3. Format query results for frontend display
4. Provide execution statistics and metadata
5. Log all executed queries for audit trail
"""

import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import hashlib
from enum import Enum

from dotenv import load_dotenv
load_dotenv()


class ExecutionStatus(Enum):
    """Status of SQL execution"""
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    ROLLBACK = "rollback"


@dataclass
class ExecutionResult:
    """Result of SQL execution"""
    status: ExecutionStatus
    rows_affected: int
    data: Optional[List[Dict[str, Any]]]
    columns: Optional[List[str]]
    execution_time_ms: float
    query_hash: str
    timestamp: str
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        return result


class DatabaseExecutor:
    """
    Executes SQL queries against connected databases and manages results.
    """
    
    def __init__(self, connection, db_type: str):
        """
        Initialize the Database Executor.
        
        Args:
            connection: Active database connection
            db_type: Type of database ('mysql', 'postgres', 'sqlite')
        """
        self.connection = connection
        self.db_type = db_type.lower()
        self.execution_history: List[ExecutionResult] = []
        self.max_history = 100  # Keep last 100 executions
        
        print(f"[DEM] Database Executor initialized for {db_type}")
    
    def execute_query(
        self,
        sql: str,
        safe_to_execute: bool = True,
        is_destructive: bool = False,
        dry_run: bool = False
    ) -> ExecutionResult:
        """
        Execute a SQL query and return formatted results.
        """
        start_time = datetime.now()
        query_hash = hashlib.md5(sql.encode()).hexdigest()[:12]
        
        # Block execution if not safe
        if not safe_to_execute:
            return ExecutionResult(
                status=ExecutionStatus.BLOCKED,
                rows_affected=0,
                data=None,
                columns=None,
                execution_time_ms=0.0,
                query_hash=query_hash,
                timestamp=start_time.isoformat(),
                error_message="Query blocked due to safety concerns",
                warnings=["Query did not pass safety validation"]
            )
        
        # Dry run mode
        if dry_run:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                rows_affected=0,
                data=None,
                columns=None,
                execution_time_ms=0.0,
                query_hash=query_hash,
                timestamp=start_time.isoformat(),
                warnings=["Dry run - query not executed"]
            )
        
        cursor = None
        try:
            cursor = self.connection.cursor()
            
            # Execute the query
            cursor.execute(sql)
            
            # --- KEY CHANGE: RELY ON CURSOR STATE, NOT STRING MATCHING ---
            # If cursor.description exists, the query returned data (SELECT, SHOW, WITH, etc.)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                if self.db_type == 'mysql':
                    # MySQL dict cursor usually returns list of dicts, but logic varies by driver setup
                    # If rows are tuples/lists:
                    if rows and isinstance(rows[0], (list, tuple)):
                        data = [dict(zip(columns, row)) for row in rows]
                    else:
                        # It's already a dict (pymysql DictCursor)
                        data = rows
                else:
                    # Standard sequence of sequences
                    data = [dict(zip(columns, row)) for row in rows]
                
                rows_affected = len(data)
            else:
                # It was a DML (INSERT, UPDATE, DELETE, DROP)
                self.connection.commit()
                rows_affected = cursor.rowcount
                data = None
                columns = None
            # -------------------------------------------------------------
            
            # Calculate execution time
            end_time = datetime.now()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000
            
            result = ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                rows_affected=rows_affected,
                data=data,
                columns=columns,
                execution_time_ms=execution_time_ms,
                query_hash=query_hash,
                timestamp=start_time.isoformat(),
                warnings=[]
            )
            
            # Add to history
            self._add_to_history(result)
            
            return result
            
        except Exception as e:
            # Rollback on error for destructive operations
            if is_destructive:
                try:
                    self.connection.rollback()
                    status = ExecutionStatus.ROLLBACK
                except Exception:
                    status = ExecutionStatus.FAILED
            else:
                status = ExecutionStatus.FAILED
            
            end_time = datetime.now()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000
            
            result = ExecutionResult(
                status=status,
                rows_affected=0,
                data=None,
                columns=None,
                execution_time_ms=execution_time_ms,
                query_hash=query_hash,
                timestamp=start_time.isoformat(),
                error_message=str(e),
                warnings=["Transaction rolled back" if status == ExecutionStatus.ROLLBACK else "Execution failed"]
            )
            
            self._add_to_history(result)
            return result
            
        finally:
            if cursor:
                cursor.close()
    
    def _add_to_history(self, result: ExecutionResult):
        """Add execution result to history, maintaining max size"""
        self.execution_history.append(result)
        if len(self.execution_history) > self.max_history:
            self.execution_history.pop(0)
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent execution history.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of execution results as dictionaries
        """
        return [result.to_dict() for result in self.execution_history[-limit:]]
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history.clear()
        print("[DEM] Execution history cleared")
    
    def format_results_for_display(self, result: ExecutionResult) -> Dict[str, Any]:
        """
        Format execution results for frontend display.
        
        Args:
            result: ExecutionResult to format
            
        Returns:
            Dictionary with formatted display data
        """
        formatted = {
            "success": result.status == ExecutionStatus.SUCCESS,
            "status": result.status.value,
            "message": self._get_status_message(result),
            "execution_time": f"{result.execution_time_ms:.2f}ms",
            "rows_affected": result.rows_affected,
            "has_data": result.data is not None and len(result.data) > 0,
            "data": result.data,
            "columns": result.columns,
            "warnings": result.warnings,
            "error": result.error_message,
            "timestamp": result.timestamp,
            "query_hash": result.query_hash
        }
        
        # Add statistics for SELECT queries
        if result.data:
            formatted["row_count"] = len(result.data)
            formatted["column_count"] = len(result.columns) if result.columns else 0
        
        return formatted
    
    def _get_status_message(self, result: ExecutionResult) -> str:
        """Generate a user-friendly status message"""
        if result.status == ExecutionStatus.SUCCESS:
            if result.data:
                return f"Query executed successfully. Retrieved {result.rows_affected} row(s)."
            else:
                return f"Query executed successfully. {result.rows_affected} row(s) affected."
        elif result.status == ExecutionStatus.BLOCKED:
            return "Query was blocked due to safety concerns."
        elif result.status == ExecutionStatus.ROLLBACK:
            return f"Query failed and was rolled back: {result.error_message}"
        else:
            return f"Query execution failed: {result.error_message}"
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test if database connection is alive.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True, "Connection is alive"
            
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        Renamed from get_statistics to match frontend calls.
        
        Returns:
            Dictionary with statistics
        """
        if not self.execution_history:
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "blocked": 0,
                "average_execution_time_ms": 0.0
            }
        
        total = len(self.execution_history)
        successful = len([r for r in self.execution_history if r.status == ExecutionStatus.SUCCESS])
        failed = len([r for r in self.execution_history if r.status == ExecutionStatus.FAILED])
        blocked = len([r for r in self.execution_history if r.status == ExecutionStatus.BLOCKED])
        avg_time = sum(r.execution_time_ms for r in self.execution_history) / total
        
        return {
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "blocked": blocked,
            "average_execution_time_ms": round(avg_time, 2),
            "success_rate": round((successful / total) * 100, 2) if total > 0 else 0.0
        }


# Example usage and testing
if __name__ == "__main__":
    
    # Create a test database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE students (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER
        )
    """)
    cursor.execute("INSERT INTO students VALUES (1, 'Alice', 20)")
    cursor.execute("INSERT INTO students VALUES (2, 'Bob', 22)")
    conn.commit()
    cursor.close()
    
    # Initialize executor
    executor = DatabaseExecutor(conn, "sqlite")
    
    # Test SELECT query
    print("\n--- Testing SELECT Query ---")
    result = executor.execute_query("SELECT * FROM students", safe_to_execute=True)
    formatted = executor.format_results_for_display(result)
    print(json.dumps(formatted, indent=2, default=str))
    
    # Test INSERT query
    print("\n--- Testing INSERT Query ---")
    result = executor.execute_query(
        "INSERT INTO students VALUES (3, 'Charlie', 21)",
        safe_to_execute=True,
        is_destructive=True
    )
    formatted = executor.format_results_for_display(result)
    print(json.dumps(formatted, indent=2, default=str))
    
    # Test statistics
    print("\n--- Execution Statistics ---")
    # --- UPDATED LINE BELOW ---
    stats = executor.get_execution_stats() 
    print(json.dumps(stats, indent=2))
    
    conn.close()