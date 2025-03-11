"""
Tests for API functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
from wikly.api import WikilyAPI

class TestWikilyAPI(unittest.TestCase):
    """Test cases for the WikilyAPI class."""

    def setUp(self):
        """Set up test fixtures."""
        self.api = WikilyAPI('https://example.com', 'fake_token')

    @patch('wikly.api.requests.post')
    def test_test_connection(self, mock_post):
        """Test the test_connection method."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'pages': {
                    'list': [
                        {'id': 1, 'title': 'Test Page'}
                    ]
                }
            }
        }
        mock_post.return_value = mock_response

        # Call the method
        result = self.api.test_connection()

        # Assert the result
        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch('wikly.api.requests.post')
    def test_test_connection_failure(self, mock_post):
        """Test the test_connection method when it fails."""
        # Mock the response to return an error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_post.return_value = mock_response

        # Call the method
        result = self.api.test_connection()

        # Assert the result
        self.assertFalse(result)
        mock_post.assert_called_once()

if __name__ == '__main__':
    unittest.main() 