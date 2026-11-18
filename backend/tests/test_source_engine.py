"""Unit and integration tests for SourceEngine:
- Python parsing (functions, classes, methods, parameters, annotations, async, imports)
- JavaScript parsing (Tree-sitter functions, classes, arrow functions, require, ES imports, exports)
- Malformed syntax handling (without crashing)
"""

from pathlib import Path
from app.engines.source_engine import SourceEngine


def test_python_parsing_normal(tmp_path: Path):
    py_code = '''"""Module docstring."""
import os
from typing import Optional, List

class DataProcessor:
    """Class docstring."""
    def __init__(self, name: str, batch_size: int = 50):
        self.name = name

    @classmethod
    def create_default(cls) -> "DataProcessor":
        return cls("default")

    async def process_items(self, items: List[str], timeout: Optional[float] = 10.0) -> int:
        """Process items asynchronously."""
        return len(items)

def helper_func(a: int, b: int = 10, *args, **kwargs) -> int:
    # inline comment
    return a + b
'''
    py_file = tmp_path / "processor.py"
    py_file.write_text(py_code, encoding="utf-8")

    engine = SourceEngine()
    result = engine.parse_python_file(py_file, "src/processor.py")

    assert result.parse_error is None
    assert result.language == "python"
    assert result.loc > 15
    assert len(result.classes) == 1
    assert result.classes[0].name == "DataProcessor"
    assert len(result.classes[0].methods) == 3

    init_method = result.classes[0].methods[0]
    assert init_method.name == "__init__"
    assert any(p.name == "batch_size" and p.default_value == "50" for p in init_method.parameters)

    async_method = result.classes[0].methods[2]
    assert async_method.name == "process_items"
    assert async_method.is_async is True
    assert async_method.return_annotation == "int"

    assert len(result.functions) == 1
    assert result.functions[0].name == "helper_func"
    assert len(result.imports) == 2
    assert "Module docstring." in result.docstrings


def test_python_malformed_syntax(tmp_path: Path):
    bad_py = "def broken_func(:\n    return 42"
    bad_file = tmp_path / "bad.py"
    bad_file.write_text(bad_py, encoding="utf-8")

    engine = SourceEngine()
    result = engine.parse_python_file(bad_file, "bad.py")

    assert result.parse_error is not None
    assert "SyntaxError" in result.parse_error
    assert result.loc == 2


def test_javascript_parsing_tree_sitter(tmp_path: Path):
    js_code = """/**
 * Math utility class
 */
class Calculator extends BaseCalc {
    constructor(precision = 2) {
        super();
        this.precision = precision;
    }

    async computeAsync(val) {
        return val * 2;
    }
}

/**
 * Add two numbers
 */
function add(a, b = 0) {
    // Return the sum
    return a + b;
}

const multiply = async (x, y) => x * y;

import { request } from 'axios';
const fs = require('fs');

export default Calculator;
export { add, multiply };
"""
    js_file = tmp_path / "calc.js"
    js_file.write_text(js_code, encoding="utf-8")

    engine = SourceEngine()
    result = engine.parse_javascript_file(js_file, "calc.js")

    assert result.parse_error is None
    assert result.language == "javascript"
    assert len(result.classes) == 1
    assert result.classes[0].name == "Calculator"
    assert "BaseCalc" in result.classes[0].bases
    assert len(result.classes[0].methods) == 2

    func_names = [f.name for f in result.functions]
    assert "add" in func_names
    assert "multiply" in func_names

    # Check params
    add_fn = next(f for f in result.functions if f.name == "add")
    assert any(p.name == "b" and p.default_value == "0" for p in add_fn.parameters)

    # Check async status
    mul_fn = next(f for f in result.functions if f.name == "multiply")
    assert mul_fn.is_async is True

    # Check imports & exports
    import_mods = [imp.module for imp in result.imports]
    assert "axios" in import_mods
    assert "fs" in import_mods
    assert len(result.exports) >= 1
