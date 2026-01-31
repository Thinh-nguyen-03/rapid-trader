import pytest
import pandas as pd
from unittest.mock import Mock, patch
from rapidtrader.data.sp500_api import iSharesClient, get_sp500_symbols


class TestiSharesClient:

    def test_initialization_default_params(self):
        client = iSharesClient()
        assert client.url is not None
        assert client.timeout > 0

    def test_initialization_custom_params(self):
        client = iSharesClient(url="https://example.com/test.csv", timeout=60)
        assert client.url == "https://example.com/test.csv"
        assert client.timeout == 60

    def test_parse_csv_valid_data(self):
        client = iSharesClient()
        csv_content = """
Fund Holdings,as of Date,
Ticker,Name,Sector,Asset Class,Weight (%)
NVDA,NVIDIA CORP,Information Technology,Equity,7.59
AAPL,APPLE INC,Information Technology,Equity,6.20
-,CASH,Cash,Cash,0.38
"""
        df = client.parse_csv(csv_content)
        assert len(df) == 2
        assert list(df.columns) == ['symbol', 'name', 'sector', 'weight']
        assert df.iloc[0]['symbol'] == 'NVDA'
        assert df.iloc[0]['weight'] == pytest.approx(7.59)

    def test_parse_csv_missing_header(self):
        client = iSharesClient()
        with pytest.raises(ValueError, match="Could not find CSV header row"):
            client.parse_csv("No,Valid,Headers\nDATA,DATA,DATA")

    def test_parse_csv_filters_non_equities(self):
        client = iSharesClient()
        csv_content = """
Ticker,Name,Sector,Asset Class,Weight (%)
AAPL,APPLE INC,Technology,Equity,6.20
-,CASH,Cash,Cash,0.50
"""
        df = client.parse_csv(csv_content)
        assert len(df) == 1
        assert df.iloc[0]['symbol'] == 'AAPL'

    @patch('rapidtrader.data.sp500_api.requests.get')
    def test_fetch_sp500_csv_success(self, mock_get):
        client = iSharesClient()
        mock_response = Mock()
        mock_response.text = "Ticker,Name\nAAPL,Apple Inc"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = client.fetch_sp500_csv()
        assert result == "Ticker,Name\nAAPL,Apple Inc"
        mock_get.assert_called_once()

    @patch('rapidtrader.data.sp500_api.requests.get')
    def test_fetch_sp500_csv_timeout(self, mock_get):
        import requests.exceptions
        client = iSharesClient(timeout=1)
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        with pytest.raises(RuntimeError, match="timed out"):
            client.fetch_sp500_csv()

    @patch('rapidtrader.data.sp500_api.requests.get')
    def test_fetch_sp500_csv_http_error(self, mock_get):
        import requests.exceptions
        client = iSharesClient()
        mock_get.side_effect = requests.exceptions.RequestException("404 Not Found")
        with pytest.raises(RuntimeError, match="API request failed"):
            client.fetch_sp500_csv()

    def test_get_constituents_adds_spy_if_missing(self):
        client = iSharesClient()
        csv_content = """
Ticker,Name,Sector,Asset Class,Weight (%)
AAPL,APPLE INC,Technology,Equity,6.20
"""
        with patch.object(client, 'fetch_sp500_csv', return_value=csv_content):
            df = client.get_constituents()
            assert 'SPY' in df['symbol'].tolist()
            assert df[df['symbol'] == 'SPY'].iloc[0]['sector'] == 'ETF'


class TestGetSP500Symbols:

    @patch('rapidtrader.data.sp500_api.iSharesClient')
    def test_get_sp500_symbols_ishares_success(self, mock_ishares_class):
        mock_client = Mock()
        mock_df = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT'],
            'sector': ['Technology', 'Technology'],
            'name': ['Apple', 'Microsoft'],
            'weight': [6.5, 5.5]
        })
        mock_client.get_constituents_with_cache.return_value = mock_df
        mock_ishares_class.return_value = mock_client

        result = get_sp500_symbols()
        assert len(result) == 2
        assert result[0] == ('AAPL', 'Technology')

    @patch('rapidtrader.data.sp500_api.iSharesClient')
    @patch('rapidtrader.data.sp500_api.settings')
    def test_get_sp500_symbols_fallback_on_error(self, mock_settings, mock_ishares_class):
        mock_settings.RT_SP500_SOURCE = "ishares"
        mock_client = Mock()
        mock_client.get_constituents_with_cache.side_effect = RuntimeError("API failure")
        mock_ishares_class.return_value = mock_client

        result = get_sp500_symbols()
        assert len(result) > 0
        assert isinstance(result[0], tuple)

    @patch('rapidtrader.data.sp500_api.settings')
    def test_get_sp500_symbols_hardcoded_mode(self, mock_settings):
        mock_settings.RT_SP500_SOURCE = "hardcoded"
        result = get_sp500_symbols()
        assert len(result) > 0
        symbols = [s for s, _ in result]
        assert 'SPY' in symbols
