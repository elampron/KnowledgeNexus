import os
import tempfile
from click.testing import CliRunner

from cli import cli
import cognitive.entity_extraction as ce
from models.entities import ExtractedEntities, EntitySchema


def dummy_extract_entities(text: str, instructions: str = "") -> ExtractedEntities:
    return ExtractedEntities(entities=[EntitySchema(name="Dummy", entity_type="Test")])


def test_cli_extract_entities_raw_text(monkeypatch):
    # Override the extraction function to avoid external API calls
    monkeypatch.setattr(ce, "extract_entities_from_text", dummy_extract_entities)
    runner = CliRunner()
    result = runner.invoke(cli, ["extract_entities", "John met Mary"], catch_exceptions=False, standalone_mode=False)
    assert result.exit_code == 0
    assert "Extracted Entities:" in result.output


def test_process_input_file(monkeypatch):
    # Override the extraction function for file input test
    monkeypatch.setattr(ce, "extract_entities_from_text", dummy_extract_entities)
    runner = CliRunner()
    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as tmp:
        tmp.write("File content")
        tmp_path = tmp.name
    try:
        result = runner.invoke(cli, ["extract_entities", tmp_path], catch_exceptions=False, standalone_mode=False)
        assert result.exit_code == 0
        assert "Extracted Entities:" in result.output
    finally:
        os.remove(tmp_path)


def test_invalid_url(monkeypatch):
    # URL input is not implemented so should result in invalid input
    monkeypatch.setattr(ce, "extract_entities_from_text", dummy_extract_entities)
    runner = CliRunner()
    result = runner.invoke(cli, ["extract_entities", "http://example.com"], catch_exceptions=False, standalone_mode=False)
    assert result.exit_code == 0
    assert "Invalid input." in result.output 