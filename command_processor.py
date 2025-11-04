#!/usr/bin/env python3
"""
Command Processing Layer for AetherDB
Handles NL interpretation, intent detection, entity extraction, and normalization
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


# ==================== ENUMS & DATA STRUCTURES ====================

class Intent(Enum):
    """Supported operation intents"""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE_TABLE = "create_table"
    ALTER_TABLE = "alter_table"
    DROP_TABLE = "drop_table"
    CREATE_DATABASE = "create_database"
    DROP_DATABASE = "drop_database"
    SHOW = "show"
    DESCRIBE = "describe"
    COUNT = "count"
    JOIN = "join"
    AGGREGATE = "aggregate"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """Extracted entity from command"""
    type: str  # 'table', 'column', 'value', 'condition', 'database'
    value: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedCommand:
    """Output of command processing"""
    raw_command: str
    normalized_command: str
    intent: Intent
    entities: Dict[str, List[Entity]]
    confidence: float
    requires_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==================== PATTERN DEFINITIONS ====================

class CommandPatterns:
    """Regex patterns for intent and entity detection"""
    
    # Intent patterns (order matters - more specific first)
    INTENT_PATTERNS = {
        Intent.CREATE_DATABASE: [
            r'\b(create|make|build|setup)\s+(a\s+)?(new\s+)?database',
            r'\binitialize\s+database',
        ],
        Intent.DROP_DATABASE: [
            r'\b(drop|delete|remove|destroy)\s+database',
        ],
        Intent.CREATE_TABLE: [
            r'\b(create|make|build|add)\s+(a\s+)?(new\s+)?table',
            r'\b(create|make)\s+.*\s+table\s+called',
            r'\btable\s+creation',
        ],
        Intent.ALTER_TABLE: [
            r'\b(alter|modify|change|update)\s+table',
            r'\b(add|remove|drop)\s+(a\s+)?column',
            r'\b(rename|change)\s+column',
        ],
        Intent.DROP_TABLE: [
            r'\b(drop|delete|remove|destroy)\s+table',
        ],
        Intent.INSERT: [
            r'\b(insert|add|create|put)\s+(a\s+)?(new\s+)?(row|record|entry|data)',
            r'\badd\s+.*\s+to\s+',
            r'\binsert\s+into',
        ],
        Intent.UPDATE: [
            r'\b(update|modify|change|edit|set)\s+',
            r'\bchange\s+.*\s+to\s+',
        ],
        Intent.DELETE: [
            r'\b(delete|remove|drop)\s+(all\s+)?(the\s+)?(rows?|records?|entries|data)',
            r'\bremove\s+.*\s+from',
        ],
        Intent.COUNT: [
            r'\b(count|how many|number of|total)',
            r'\bcount\s+',
        ],
        Intent.SHOW: [
            r'\b(show|display|list|get|fetch|retrieve|find)\s+(me\s+)?(all\s+)?(the\s+)?',
            r'\b(select|query)',
        ],
        Intent.DESCRIBE: [
            r'\b(describe|explain|show structure|schema of)',
            r'\bwhat\s+(is|are)\s+the\s+(structure|fields|columns)',
        ],
        Intent.JOIN: [
            r'\bjoin\s+',
            r'\bcombine\s+.*\s+with',
            r'\bmerge\s+',
        ],
        Intent.SELECT: [
            r'\bselect\s+',
            r'\bwhere\s+',
        ],
    }
    
    # Entity extraction patterns
    TABLE_PATTERNS = [
        r'\btable\s+(?:called\s+|named\s+)?["\']?(\w+)["\']?',
        r'\bfrom\s+["\']?(\w+)["\']?',
        r'\binto\s+["\']?(\w+)["\']?',
        r'\b(?:in|of)\s+(?:the\s+)?["\']?(\w+)["\']?\s+table',
    ]
    
    COLUMN_PATTERNS = [
        r'\bcolumn[s]?\s+["\']?(\w+)["\']?',
        r'\bfield[s]?\s+["\']?(\w+)["\']?',
        r'\bwhere\s+["\']?(\w+)["\']?\s*[=<>!]',
        r'\bset\s+["\']?(\w+)["\']?\s*=',
    ]
    
    DATABASE_PATTERNS = [
        r'\bdatabase\s+(?:called\s+|named\s+)?["\']?(\w+)["\']?',
        r'\buse\s+["\']?(\w+)["\']?',
    ]
    
    # Condition patterns
    CONDITION_PATTERNS = [
        r'\bwhere\s+(.+?)(?:\s+and\s+|\s+or\s+|$)',
        r'\b(?:greater|less|more|fewer)\s+than\s+(\d+)',
        r'\bequals?\s+["\']?([^"\']+)["\']?',
        r'\bstarts?\s+with\s+["\']?(\w+)["\']?',
        r'\bends?\s+with\s+["\']?(\w+)["\']?',
        r'\bcontains?\s+["\']?(\w+)["\']?',
    ]
    
    # Value patterns
    VALUE_PATTERNS = [
        r'=\s*["\']?([^"\']+)["\']?',
        r'\bvalue[s]?\s+["\']?([^"\']+)["\']?',
    ]


# ==================== COMMAND PROCESSOR ====================

class CommandProcessor:
    """
    Main command processing engine
    Analyzes NL input and extracts structured information
    """
    
    def __init__(self, schema_snapshot: Optional[Dict] = None):
        self.schema = schema_snapshot or {}
        self.session_context = {
            "active_database": None,
            "active_table": None,
            "last_command": None,
        }
        
    def process(self, raw_command: str) -> ParsedCommand:
        """
        Main entry point - processes raw NL command
        
        Args:
            raw_command: Natural language command from user
            
        Returns:
            ParsedCommand object with intent, entities, and metadata
        """
        # Step 1: Normalize input
        normalized = self._normalize_command(raw_command)
        
        # Step 2: Detect intent
        intent, intent_confidence = self._detect_intent(normalized)
        
        # Step 3: Extract entities
        entities = self._extract_entities(normalized, intent)
        
        # Step 4: Validate against schema
        validated_entities = self._validate_entities(entities)
        
        # Step 5: Check if clarification needed
        requires_clarification, questions = self._check_clarification(
            intent, validated_entities
        )
        
        # Step 6: Calculate overall confidence
        overall_confidence = self._calculate_confidence(
            intent_confidence, validated_entities
        )
        
        # Step 7: Build metadata
        metadata = self._build_metadata(intent, validated_entities)
        
        return ParsedCommand(
            raw_command=raw_command,
            normalized_command=normalized,
            intent=intent,
            entities=validated_entities,
            confidence=overall_confidence,
            requires_clarification=requires_clarification,
            clarification_questions=questions,
            metadata=metadata
        )
    
    def _normalize_command(self, command: str) -> str:
        """Clean and normalize input command"""
        # Convert to lowercase
        normalized = command.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Expand contractions
        contractions = {
            "don't": "do not",
            "won't": "will not",
            "can't": "cannot",
            "shouldn't": "should not",
            "'s": " is",
            "'re": " are",
            
            
        }
        for contraction, expansion in contractions.items():
            normalized = normalized.replace(contraction, expansion)
        
        # Remove punctuation except quotes (which might be part of values)
        normalized = re.sub(r'[^\w\s"\']', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _detect_intent(self, command: str) -> Tuple[Intent, float]:
        """
        Detect user intent from normalized command
        Returns (Intent, confidence_score)
        """
        # Check each intent pattern
        for intent, patterns in CommandPatterns.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    # Calculate confidence based on pattern specificity
                    confidence = 0.9 if len(patterns) == 1 else 0.8
                    return intent, confidence
        
        # Fallback: try to guess from keywords
        if any(kw in command for kw in ['show', 'get', 'fetch', 'display', 'list']):
            return Intent.SELECT, 0.6
        
        return Intent.UNKNOWN, 0.3
    
    def _extract_entities(self, command: str, intent: Intent) -> Dict[str, List[Entity]]:
        """Extract entities (tables, columns, values, conditions) from command"""
        entities = {
            "tables": [],
            "columns": [],
            "databases": [],
            "conditions": [],
            "values": [],
        }
        
        # Extract tables
        for pattern in CommandPatterns.TABLE_PATTERNS:
            matches = re.finditer(pattern, command, re.IGNORECASE)
            for match in matches:
                table_name = match.group(1)
                entities["tables"].append(Entity(
                    type="table",
                    value=table_name,
                    confidence=0.9
                ))
        
        # Extract columns
        for pattern in CommandPatterns.COLUMN_PATTERNS:
            matches = re.finditer(pattern, command, re.IGNORECASE)
            for match in matches:
                col_name = match.group(1)
                entities["columns"].append(Entity(
                    type="column",
                    value=col_name,
                    confidence=0.8
                ))
        
        # Extract databases
        for pattern in CommandPatterns.DATABASE_PATTERNS:
            matches = re.finditer(pattern, command, re.IGNORECASE)
            for match in matches:
                db_name = match.group(1)
                entities["databases"].append(Entity(
                    type="database",
                    value=db_name,
                    confidence=0.9
                ))
        
        # Extract conditions
        for pattern in CommandPatterns.CONDITION_PATTERNS:
            matches = re.finditer(pattern, command, re.IGNORECASE)
            for match in matches:
                condition = match.group(1)
                entities["conditions"].append(Entity(
                    type="condition",
                    value=condition,
                    confidence=0.7
                ))
        
        # Extract values
        for pattern in CommandPatterns.VALUE_PATTERNS:
            matches = re.finditer(pattern, command, re.IGNORECASE)
            for match in matches:
                value = match.group(1)
                entities["values"].append(Entity(
                    type="value",
                    value=value,
                    confidence=0.7
                ))
        
        # Remove duplicates
        for key in entities:
            seen = set()
            unique_entities = []
            for entity in entities[key]:
                if entity.value not in seen:
                    seen.add(entity.value)
                    unique_entities.append(entity)
            entities[key] = unique_entities
        
        return entities
    
    def _validate_entities(self, entities: Dict[str, List[Entity]]) -> Dict[str, List[Entity]]:
        """Validate entities against schema if available"""
        if not self.schema:
            return entities
        
        validated = entities.copy()
        
        # Validate tables
        for table_entity in validated.get("tables", []):
            if table_entity.value in self.schema.get("tables", []):
                table_entity.confidence = 1.0
                table_entity.metadata["validated"] = True
            else:
                table_entity.confidence *= 0.5
                table_entity.metadata["validated"] = False
                table_entity.metadata["warning"] = "Table not found in schema"
        
        return validated
    
    def _check_clarification(
        self, 
        intent: Intent, 
        entities: Dict[str, List[Entity]]
    ) -> Tuple[bool, List[str]]:
        """Determine if user clarification is needed"""
        questions = []
        
        # Check for missing critical entities based on intent
        if intent in [Intent.SELECT, Intent.UPDATE, Intent.DELETE]:
            if not entities.get("tables"):
                questions.append("Which table would you like to work with?")
        
        if intent == Intent.INSERT:
            if not entities.get("tables"):
                questions.append("Which table should I insert data into?")
            if not entities.get("values"):
                questions.append("What values should I insert?")
        
        if intent in [Intent.CREATE_TABLE, Intent.ALTER_TABLE]:
            if not entities.get("tables"):
                questions.append("What should the table be called?")
        
        if intent == Intent.UPDATE and not entities.get("conditions"):
            questions.append("Which rows should I update? (Please specify a condition)")
        
        if intent == Intent.DELETE and not entities.get("conditions"):
            questions.append("⚠️ WARNING: This will delete ALL rows. Please confirm or add a condition.")
        
        return len(questions) > 0, questions
    
    def _calculate_confidence(
        self,
        intent_confidence: float,
        entities: Dict[str, List[Entity]]
    ) -> float:
        """Calculate overall confidence score"""
        # Start with intent confidence
        confidence = intent_confidence
        
        # Adjust based on entity extraction
        total_entities = sum(len(ent_list) for ent_list in entities.values())
        if total_entities > 0:
            entity_confidence = sum(
                e.confidence for ent_list in entities.values() for e in ent_list
            ) / total_entities
            confidence = (confidence + entity_confidence) / 2
        else:
            confidence *= 0.7  # Penalize if no entities found
        
        return round(confidence, 2)
    
    def _build_metadata(
        self,
        intent: Intent,
        entities: Dict[str, List[Entity]]
    ) -> Dict[str, Any]:
        """Build metadata for downstream processing"""
        metadata = {
            "destructive": intent in [
                Intent.DELETE, Intent.DROP_TABLE, Intent.DROP_DATABASE, Intent.ALTER_TABLE
            ],
            "modifies_schema": intent in [
                Intent.CREATE_TABLE, Intent.ALTER_TABLE, Intent.DROP_TABLE,
                Intent.CREATE_DATABASE, Intent.DROP_DATABASE
            ],
            "modifies_data": intent in [Intent.INSERT, Intent.UPDATE, Intent.DELETE],
            "entity_count": {
                key: len(value) for key, value in entities.items()
            },
        }
        
        return metadata
    
    def update_schema(self, schema: Dict):
        """Update internal schema snapshot"""
        self.schema = schema
    
    def update_context(self, **kwargs):
        """Update session context"""
        self.session_context.update(kwargs)


# ==================== TESTING & DEMO ====================

def demo():
    """Demonstrate command processor capabilities"""
    print("=" * 60)
    print("Command Processing Layer - Demo")
    print("=" * 60)
    
    # Initialize processor
    processor = CommandProcessor(schema_snapshot={
        "tables": ["employees", "departments", "projects"]
    })
    
    # Test commands
    test_commands = [
        "Show me all employees in the Engineering department",
        "Create a new table called interns with fields name, school, start_date",
        "Count how many projects exist",
        "Delete all records from employees where salary < 50000",
        "Update the status to Active for employee id 123",
        "Add a new employee named John Doe to the employees table",
        "Show me employees whose surname starts with A",
        "Drop the temporary_logs table",
    ]
    
    for cmd in test_commands:
        print(f"\n{'─' * 60}")
        print(f"Command: {cmd}")
        print(f"{'─' * 60}")
        
        result = processor.process(cmd)
        
        print(f"Intent: {result.intent.value}")
        print(f"Confidence: {result.confidence}")
        print(f"Normalized: {result.normalized_command}")
        print("\nEntities:")
        for entity_type, entity_list in result.entities.items():
            if entity_list:
                print(f"  {entity_type}:")
                for entity in entity_list:
                    print(f"    - {entity.value} (confidence: {entity.confidence})")
        
        print("\nMetadata:")
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")
        
        if result.requires_clarification:
            print("\n⚠️  Clarification Required:")
            for question in result.clarification_questions:
                print(f"  - {question}")


if __name__ == "__main__":
    demo()