# RapidTrader Operations Runbook

Comprehensive operational guide for running and maintaining the RapidTrader system.

## 🚨 Emergency Procedures

### System Down / Not Responding
1. **Check system status**: Database connectivity, API health
2. **Review logs**: Check recent error messages and exceptions
3. **Restart services**: Stop and restart application components
4. **Verify data**: Ensure data integrity after restart
5. **Escalate**: Contact system administrator if issues persist

### Data Pipeline Failure
1. **Identify scope**: Which symbols/dates are affected
2. **Check data sources**: FMP API status, yfinance availability
3. **Manual re-run**: Execute failed jobs with specific parameters
4. **Validate results**: Verify data completeness and quality
5. **Update monitoring**: Adjust alerts if systematic issue

### Trading Job Failure
1. **Stop all jobs**: Prevent partial or incorrect orders
2. **Assess impact**: Check which signals/orders were affected
3. **Manual review**: Validate any generated orders before execution
4. **Fix and rerun**: Address root cause and re-execute
5. **Reconcile**: Ensure all positions and orders are correct

## 📅 Daily Operations

### Pre-Market Checklist (Before 9:30 AM ET)
- [ ] **System Health**: All services running normally
- [ ] **Data Validation**: Previous day's data complete
- [ ] **Error Review**: Check overnight logs for issues
- [ ] **API Status**: Verify FMP and yfinance availability
- [ ] **Database Space**: Confirm adequate storage available
- [ ] **Backup Status**: Verify automated backups completed

### Post-Market Operations (After 4:00 PM ET)
- [ ] **Start EOD Jobs**: Initiate data ingestion pipeline
- [ ] **Monitor Progress**: Track job execution status
- [ ] **Validate Data**: Verify OHLCV data completeness
- [ ] **Review Signals**: Check generated trading signals
- [ ] **Risk Validation**: Confirm risk constraints enforced
- [ ] **Generate Reports**: Create daily performance summary

### End-of-Day Checklist (Before 8:00 PM ET)
- [ ] **Job Completion**: All EOD jobs finished successfully
- [ ] **Data Quality**: No anomalies or missing data
- [ ] **Signal Review**: Trading signals generated appropriately
- [ ] **Risk Compliance**: All risk limits respected
- [ ] **Report Generation**: Daily reports created and distributed
- [ ] **Log Archive**: Clean up temporary files and logs

## 📊 Monitoring and Alerting

### Key Metrics to Monitor

#### System Health
- **Job Success Rate**: >99% of daily jobs complete successfully
- **Processing Time**: EOD workflow completes within 30 minutes
- **Memory Usage**: Peak memory usage <2GB
- **Database Connections**: <80% of connection pool utilized
- **API Response Time**: Average response time <5 seconds

#### Data Quality
- **Symbol Coverage**: >95% of S&P 500 symbols have current data
- **Data Completeness**: <1% missing OHLCV data points
- **Price Anomalies**: <0.1% of prices outside expected ranges
- **Volume Anomalies**: <0.5% of volume data appears incorrect
- **Indicator Calculations**: <0.1% calculation errors

#### Trading System
- **Signal Generation**: Signals generated for >5% of universe
- **Risk Constraint Violations**: 0 violations of risk limits
- **Order Generation**: Orders created within risk parameters
- **Market Filter**: SPY gate functioning correctly
- **Sector Exposure**: All sectors within specified limits

### Alert Thresholds

#### Critical Alerts (Immediate Response Required)
- Any job failure or exception
- Database connection failures
- API rate limit exceeded
- Risk constraint violations
- Data corruption detected

#### Warning Alerts (Review Within 1 Hour)
- Processing time >45 minutes
- Data completeness <98%
- Memory usage >1.5GB
- API response time >10 seconds
- Missing signals for major symbols

#### Info Alerts (Review Next Business Day)
- Processing time >30 minutes
- Data completeness <99%
- Unusual market volatility detected
- New symbols added/removed from S&P 500
- Monthly/quarterly reports generated

### Monitoring Tools

#### Log Analysis
```bash
# Check recent errors
tail -100 /var/log/rapidtrader/application.log | grep ERROR

# Monitor job execution
grep "Job completed" /var/log/rapidtrader/jobs.log | tail -10

# Check API usage
grep "API call" /var/log/rapidtrader/api.log | wc -l
```

#### Database Monitoring
```sql
-- Check data completeness
SELECT symbol, COUNT(*) as days_of_data 
FROM bars_daily 
WHERE d >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY symbol 
HAVING COUNT(*) < 20;

-- Review recent signals
SELECT strategy, direction, COUNT(*) 
FROM signals_daily 
WHERE d = CURRENT_DATE - 1
GROUP BY strategy, direction;

-- Check system performance
SELECT 
    AVG(EXTRACT(EPOCH FROM (finished_at - started_at))) as avg_runtime_seconds
FROM job_log 
WHERE job_name = 'eod_ingest' 
    AND started_at >= CURRENT_DATE - INTERVAL '7 days';
```

#### Health Check Scripts
```bash
# System health check
python scripts/health_check.py --all

# Data quality validation  
python scripts/validate_data.py --date yesterday

# API connectivity test
python scripts/test_apis.py --verbose
```

## 🔧 Maintenance Procedures

### Weekly Maintenance

#### Data Cleanup
- Archive logs older than 30 days
- Clean up temporary files and cache
- Vacuum database tables for performance
- Update symbol universe from FMP
- Review and rotate API keys if needed

#### Performance Review
- Analyze job execution times
- Review memory usage patterns
- Check database query performance
- Validate indicator calculation accuracy
- Monitor API usage and costs

### Monthly Maintenance

#### System Updates
- Update Python packages (security patches)
- Review and update configuration parameters
- Test backup and recovery procedures
- Validate monitoring and alerting
- Review system capacity and scaling needs

#### Data Validation
- Comprehensive data quality audit
- Validate historical indicator calculations
- Review strategy performance metrics
- Analyze risk management effectiveness
- Update symbol universe and sectors

### Quarterly Maintenance

#### System Optimization
- Database performance tuning
- Code refactoring and optimization
- Infrastructure capacity planning
- Security review and updates
- Documentation updates

#### Strategy Review
- Backtest strategy performance
- Analyze risk-adjusted returns
- Review parameter optimization
- Evaluate new strategy opportunities
- Update risk management rules

## 🐛 Troubleshooting Guide

### Common Issues

#### "No data received for symbol XXX"
**Cause**: Symbol may be delisted, suspended, or API issue
**Solution**: 
1. Check if symbol is still in S&P 500
2. Verify symbol spelling and format
3. Test API directly for the symbol
4. Mark symbol as inactive if delisted

#### "Database connection failed"
**Cause**: Network issue, database down, or connection limit
**Solution**:
1. Test database connectivity
2. Check connection string and credentials
3. Verify database service status
4. Restart application if connection pool exhausted

#### "API rate limit exceeded"
**Cause**: Too many API calls in short time period
**Solution**:
1. Check current API usage
2. Implement delays between API calls
3. Consider upgrading API plan
4. Cache responses to reduce calls

#### "Signal generation failed for strategy XXX"
**Cause**: Insufficient data, calculation error, or logic bug
**Solution**:
1. Check required data availability
2. Validate indicator calculations
3. Review strategy logic and parameters
4. Test with known good data

#### "Risk constraint violation"
**Cause**: Position would exceed sector/portfolio limits
**Solution**:
1. Review current portfolio exposure
2. Validate risk calculation logic
3. Check if limits need adjustment
4. Ensure risk rules are current

### Performance Issues

#### Slow Job Execution
**Possible Causes**:
- Database performance degradation
- Large number of symbols to process
- API response time slowdown
- Memory constraints

**Solutions**:
- Optimize database queries
- Implement parallel processing
- Cache frequently accessed data
- Increase system resources

#### High Memory Usage
**Possible Causes**:
- Memory leaks in calculations
- Large datasets kept in memory
- Inefficient data structures

**Solutions**:
- Profile memory usage
- Implement data streaming
- Optimize pandas operations
- Add garbage collection

#### Database Lock Timeouts
**Possible Causes**:
- Long-running transactions
- Concurrent access conflicts
- Poor query optimization

**Solutions**:
- Optimize transaction scope
- Add proper indexing
- Implement connection pooling
- Review query execution plans

## 📚 Reference Information

### Configuration Parameters

#### Required Environment Variables
```bash
# Database connection
RT_DB_URL="postgresql://user:pass@host:port/db"

# API keys
RT_FMP_API_KEY="your_fmp_api_key"

# Capital and risk settings
RT_START_CAPITAL=100000.0
RT_PCT_PER_TRADE=0.05
RT_DAILY_RISK_CAP=0.005
RT_MAX_EXPOSURE_PER_SECTOR=0.30
```

#### Optional Parameters
```bash
# Market filter settings
RT_MARKET_FILTER_ENABLE=1
RT_MARKET_FILTER_SMA=200
RT_MARKET_FILTER_SYMBOL="SPY"

# Signal confirmation
RT_ENABLE_SIGNAL_CONFIRM=1
RT_CONFIRM_WINDOW=3
RT_CONFIRM_MIN_COUNT=2

# ATR stops
RT_ENABLE_ATR_STOP=1
RT_ATR_LOOKBACK=14
RT_ATR_STOP_K=3.0
RT_COOLDOWN_DAYS_ON_STOP=1
```

### Command Reference

#### Data Management
```bash
# Update S&P 500 symbols
python scripts/seed_sp500.py

# Ingest historical data
python -m rapidtrader.jobs.eod_ingest --days 365

# Validate data quality
python scripts/validate_data.py --date 2024-01-15
```

#### Job Execution
```bash
# Run full EOD workflow
python scripts/run_eod_workflow.py

# Generate signals only
python -m rapidtrader.jobs.eod_trade --signals-only

# Create reports
python -m rapidtrader.jobs.eod_report --email
```

#### System Maintenance
```bash
# Health check
python scripts/health_check.py

# Clean old logs
python scripts/cleanup_logs.py --days 30

# Database maintenance
python scripts/db_maintenance.py --vacuum
```

### Log File Locations

#### Application Logs
- **Main Application**: `/var/log/rapidtrader/application.log`
- **Job Execution**: `/var/log/rapidtrader/jobs.log`
- **API Calls**: `/var/log/rapidtrader/api.log`
- **Database**: `/var/log/rapidtrader/database.log`
- **Errors**: `/var/log/rapidtrader/error.log`

#### Log Rotation
- Logs rotate daily at midnight
- Keep 30 days of historical logs
- Compress logs older than 7 days
- Archive monthly logs to long-term storage

### Contact Information

#### Primary Support
- **System Administrator**: admin@company.com
- **On-Call Phone**: +1-555-SUPPORT
- **Slack Channel**: #rapidtrader-alerts

#### Escalation
- **Technical Lead**: tech-lead@company.com
- **Management**: manager@company.com
- **Emergency After Hours**: +1-555-EMERGENCY

### External Dependencies

#### Data Providers
- **Financial Modeling Prep**: support@financialmodelingprep.com
- **Yahoo Finance**: No direct support (free service)

#### Infrastructure
- **Supabase Support**: support@supabase.io
- **AWS Support**: Via AWS console
- **Hosting Provider**: Per hosting agreement

#### Monitoring Services
- **Uptime Monitoring**: StatusPage or similar
- **Error Tracking**: Sentry or similar
- **Performance Monitoring**: New Relic or similar

Remember: This runbook should be updated regularly as the system evolves. Always test procedures in a non-production environment before applying to production systems.
