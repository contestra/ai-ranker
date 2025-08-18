"""
Comprehensive tests for Prompter V7 implementation
Tests deduplication, provider probing, and integration with existing system
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from prompter.utils_prompting import canonicalize, calc_config_hash, is_sqlite, infer_provider
import os
from prompter.provider_probe import _fake_probe_response, probe_langchain


class TestCanonicalizeUtils:
    """Test canonicalization utilities"""
    
    def test_canonicalize_basic(self):
        """Test basic canonicalization"""
        config = {
            "Prompt": "  Test prompt  ",
            "Temperature": 0.7,
            "unused": None
        }
        
        result = canonicalize(config)
        
        assert "prompt" in result  # Lowercase key
        assert result["prompt"] == "Test prompt"  # Trimmed value
        assert "unused" not in result  # None values removed
        assert result["temperature"] == 0.7
    
    def test_canonicalize_nested(self):
        """Test nested structure canonicalization"""
        config = {
            "model": {
                "Name": "GPT-4",
                "Settings": {
                    "Temperature": 0.5,
                    "empty": None
                }
            }
        }
        
        result = canonicalize(config)
        
        assert result["model"]["name"] == "GPT-4"
        assert result["model"]["settings"]["temperature"] == 0.5
        assert "empty" not in result["model"]["settings"]
    
    def test_calc_config_hash(self):
        """Test config hash calculation"""
        config1 = {"prompt": "Test", "temperature": 0.7}
        config2 = {"temperature": 0.7, "prompt": "Test"}  # Different order
        config3 = {"prompt": "Different", "temperature": 0.7}
        
        hash1 = calc_config_hash(config1)
        hash2 = calc_config_hash(config2)
        hash3 = calc_config_hash(config3)
        
        assert hash1 == hash2  # Order doesn't matter
        assert hash1 != hash3  # Different content
        assert len(hash1) == 64  # SHA256 hex length
    
    def test_infer_provider(self):
        """Test provider inference from model ID"""
        assert infer_provider("gpt-4o") == "openai"
        assert infer_provider("gpt-5-mini") == "openai"
        assert infer_provider("o3-mini") == "openai"
        assert infer_provider("omni-large") == "openai"
        
        assert infer_provider("gemini-2.5-pro") == "google"
        assert infer_provider("models/gemini-pro") == "google"
        assert infer_provider("bison-001") == "google"
        
        assert infer_provider("claude-3-5-sonnet") == "anthropic"
        assert infer_provider("anthropic-claude-v2") == "anthropic"
        
        assert infer_provider("llama-3") is None
        assert infer_provider("unknown-model") is None


class TestProviderProbe:
    """Test provider probe functionality"""
    
    def test_fake_probe_openai(self):
        """Test fake probe for OpenAI"""
        result = _fake_probe_response("openai", "gpt-4o")
        assert result.startswith("fp_stub_")
        assert len(result) == 16  # fp_stub_ + 8 chars
    
    def test_fake_probe_google(self):
        """Test fake probe for Google/Gemini"""
        result = _fake_probe_response("google", "gemini-2.5-pro")
        assert result == "gemini-2.5-pro-stub-001"
        
        result = _fake_probe_response("gemini", "gemini-pro")
        assert result == "gemini-pro-stub-001"
    
    def test_fake_probe_anthropic(self):
        """Test fake probe for Anthropic"""
        result = _fake_probe_response("anthropic", "claude-3-5-sonnet")
        assert result.startswith("claude-")
        assert len(result) == 15  # claude- (7) + 8 chars
    
    @pytest.mark.asyncio
    async def test_probe_langchain_disabled(self):
        """Test probe when disabled via environment"""
        with patch.dict(os.environ, {"PROMPTER_PROBE_DISABLED": "true"}):
            result, captured_at = await probe_langchain("openai", "gpt-4o")
            assert result is None
            assert isinstance(captured_at, datetime)
    
    @pytest.mark.asyncio
    async def test_probe_langchain_with_mock_adapter(self):
        """Test probe with mocked LangChain adapter"""
        from unittest.mock import AsyncMock
        
        mock_adapter = MagicMock()
        # Use AsyncMock for async method
        mock_adapter.analyze_with_gpt4 = AsyncMock(return_value={
            "content": "OK",
            "system_fingerprint": "fp_12345678"
        })
        
        with patch.dict(os.environ, {"PROMPTER_PROBE_DISABLED": "false"}):
            # Pass the mock adapter directly
            result, captured_at = await probe_langchain("openai", "gpt-4o", mock_adapter)
            assert result == "fp_12345678"
            assert isinstance(captured_at, datetime)


class TestWorkspaceIntegration:
    """Test workspace and organization integration"""
    
    def test_workspace_creation(self):
        """Test workspace creation logic"""
        from app.services.prompt_versions import get_or_create_workspace
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.database import Base
        
        # Use PostgreSQL database for testing
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            pytest.skip("DATABASE_URL not set, skipping database test")
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # First, create organization
        from app.models.prompt_v7 import Organization
        org = Organization(id="test-org", name="Test Organization")
        db.add(org)
        db.commit()
        
        # Test workspace creation
        workspace = get_or_create_workspace(db, "test-org", "TestBrand")
        assert workspace.brand_name == "TestBrand"
        assert workspace.org_id == "test-org"
        assert workspace.name == "TestBrand Workspace"
        
        # Test idempotency
        workspace2 = get_or_create_workspace(db, "test-org", "TestBrand")
        assert workspace2.id == workspace.id
        
        db.close()


class TestDeduplication:
    """Test prompt template deduplication"""
    
    def test_duplicate_detection(self):
        """Test that duplicates are detected within workspace"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.database import Base
        from app.models.prompt_v7 import Organization, Workspace, PromptTemplateV7
        import uuid
        
        # Create in-memory database
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            pytest.skip("DATABASE_URL not set, skipping database test")
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Setup organization and workspace
        org = Organization(id="test-org", name="Test")
        workspace = Workspace(
            id=str(uuid.uuid4()),
            org_id="test-org",
            brand_name="TestBrand",
            name="Test Workspace"
        )
        db.add(org)
        db.add(workspace)
        db.flush()
        
        # Create first template
        config = {"prompt": "Test prompt", "temperature": 0.7}
        config_hash = calc_config_hash(config)
        
        template1 = PromptTemplateV7(
            id=str(uuid.uuid4()),
            org_id="test-org",
            workspace_id=workspace.id,
            name="Template 1",
            config=config,
            config_hash=config_hash
        )
        db.add(template1)
        db.commit()
        
        # Check for duplicate
        duplicate = db.query(PromptTemplateV7).filter_by(
            org_id="test-org",
            workspace_id=workspace.id,
            config_hash=config_hash,
            deleted_at=None
        ).first()
        
        assert duplicate is not None
        assert duplicate.id == template1.id
        
        # Different workspace should not be duplicate
        workspace2 = Workspace(
            id=str(uuid.uuid4()),
            org_id="test-org",
            brand_name="OtherBrand",
            name="Other Workspace"
        )
        db.add(workspace2)
        db.flush()
        
        no_duplicate = db.query(PromptTemplateV7).filter_by(
            org_id="test-org",
            workspace_id=workspace2.id,
            config_hash=config_hash,
            deleted_at=None
        ).first()
        
        assert no_duplicate is None
        
        db.close()


class TestVersionTracking:
    """Test provider version tracking"""
    
    def test_version_upsert(self):
        """Test version record upsert logic"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.database import Base
        from app.models.prompt_v7 import Organization, Workspace, PromptVersion
        import uuid
        
        # Create in-memory database
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            pytest.skip("DATABASE_URL not set, skipping database test")
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Setup
        org = Organization(id="test-org", name="Test")
        workspace = Workspace(
            id=str(uuid.uuid4()),
            org_id="test-org",
            brand_name="TestBrand",
            name="Test Workspace"
        )
        db.add(org)
        db.add(workspace)
        db.flush()
        
        # First version record
        now = datetime.now(timezone.utc)
        version = PromptVersion(
            id=str(uuid.uuid4()),
            org_id="test-org",
            workspace_id=workspace.id,
            provider="openai",
            model_id="gpt-4o",
            provider_version_key="fp_12345678",
            first_seen_at=now,
            last_seen_at=now,
            probe_count=1
        )
        db.add(version)
        db.commit()
        
        # Query and update
        existing = db.query(PromptVersion).filter_by(
            org_id="test-org",
            workspace_id=workspace.id,
            provider="openai",
            model_id="gpt-4o"
        ).first()
        
        assert existing is not None
        assert existing.probe_count == 1
        assert existing.provider_version_key == "fp_12345678"
        
        # Update probe count
        existing.probe_count += 1
        existing.provider_version_key = "fp_87654321"
        db.commit()
        
        # Verify update
        updated = db.query(PromptVersion).filter_by(
            org_id="test-org",
            workspace_id=workspace.id,
            provider="openai",
            model_id="gpt-4o"
        ).first()
        
        assert updated.probe_count == 2
        assert updated.provider_version_key == "fp_87654321"
        
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])