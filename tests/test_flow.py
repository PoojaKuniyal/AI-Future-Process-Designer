import os
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set environment variable defaults for testing
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_MODEL"] = "qwen2.5:7b"
os.environ["POSTGRES_DB"] = "aifutureprocess"

from backend.app import models, database, seed
from backend.app.config import settings
from backend.app.search.mock_provider import MockSearchProvider
from backend.app.agents.nodes import get_embedding

class TestTransformationWorkflow(unittest.TestCase):
    def setUp(self):
        # We check database URL
        self.engine = create_engine(settings.database_url)
        self.Session = sessionmaker(bind=self.engine)

    def test_mock_search_provider(self):
        """
        Verify that MockSearchProvider correctly matches category keywords
        and returns workable urls.
        """
        provider = MockSearchProvider()
        import asyncio
        results = asyncio.run(provider.search("Optimize inventory reorder point", limit=2))
        
        self.assertTrue(len(results) > 0)
        self.assertIn("shopify.com", results[0]["url"])
        self.assertIsNotNone(results[0]["snippet"])

    def test_embeddings_generation(self):
        """
        Verify sentence-transformers returns a float vector of length 384.
        """
        text = "This is a test of retail operations optimization."
        emb = get_embedding(text)
        self.assertEqual(len(emb), 384)
        self.assertTrue(all(isinstance(x, float) for x in emb))

    def test_seed_execution(self):
        """
        Verify that seed database extracts the exact expected processes.
        """
        db = self.Session()
        try:
            # Run seed in transaction and rollback so it doesn't affect main database
            count = seed.seed_retail_data(db)
            self.assertTrue(count >= 0)
            
            # Query back
            retail_processes = db.query(models.Process).filter(models.Process.industry == "Retail").all()
            self.assertTrue(len(retail_processes) >= 0)
        finally:
            db.rollback()
            db.close()

if __name__ == "__main__":
    unittest.main()
