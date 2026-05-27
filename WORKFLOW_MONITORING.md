# Workflow Monitoring Guide

This guide explains how to verify that your scheduled GitHub Actions workflows are running correctly and collecting data.

## Overview

You have two main workflows configured:

### 1. **Aggregator Market Update** (17k items)
- **Schedule**: Every 6 hours at specific UTC times
- **Times**: `03:30`, `09:30`, `15:30`, `21:30` UTC
- **EST equivalent**: `11:30 PM`, `5:30 AM`, `11:30 AM`, `5:30 PM`
- **Task**: Collects current market prices from the Steam aggregator
- **Database**: Writes to Supabase (production)

### 2. **Database Maintenance** (Pruning)
- **Schedule**: Every Sunday at `08:00` UTC
- **EST equivalent**: `04:00 AM` EST
- **Task**: Prunes and downsamples historical data
- **Database**: Writes to Supabase (production)

## How to Check Workflow Status

### Option 1: GitHub UI (Easiest)

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Look at the workflow runs list
4. Check for:
   - ✅ **Green checkmarks** = successful runs
   - ❌ **Red Xs** = failed runs
   - ⏳ **In progress** = currently running

### Option 2: View Detailed Logs

1. Click on a specific workflow run
2. Click "Run Aggregator Task" or "Run Pruning Task" step
3. Look for these key outputs:
   - `Items collected: XXXX`
   - `Duration: XXs`
   - Exit code `0` = success

### Option 3: Check Artifacts

Recent workflow runs upload logs as artifacts:
- `aggregator-logs-{run-id}` - Contains aggregator task logs
- `maintenance-logs-{run-id}` - Contains pruning task logs

To download:
1. Go to the workflow run
2. Scroll to bottom
3. Click on the artifact to download

## Verifying Data Collection

### Check Database Directly (If You Have Supabase Access)

1. Go to your [Supabase Dashboard](https://supabase.com)
2. Navigate to your project
3. Open the SQL editor
4. Run this query to see recent collection runs:

```sql
SELECT 
    started_at,
    finished_at,
    status,
    total_items,
    successful,
    failed,
    duration_seconds
FROM collection_runs
WHERE started_at > now() - interval '7 days'
ORDER BY started_at DESC
LIMIT 20;
```

### Check Price Updates

```sql
SELECT 
    COUNT(*) as total_prices,
    MAX(recorded_at) as latest_update
FROM price_history
WHERE recorded_at > now() - interval '1 day';
```

## Expected Patterns

### Healthy Workflow
- Runs appear **on schedule** (within a few minutes of the scheduled time)
- All runs show ✅ **SUCCESS**
- Duration is **15-60 seconds** (typical for 17k item collection)
- Each run collects approximately **15,000-17,000 items**
- Price updates accumulate steadily

### Warning Signs
- Runs **frequently failing** (❌)
- Runs **not appearing** at expected times
- Runs taking **longer than 2 minutes**
- Logs showing **high error counts**
- Database not receiving updates despite successful runs

## Troubleshooting

### Workflow Didn't Run at Scheduled Time

1. **Check GitHub Status**: GitHub Actions may be experiencing issues
2. **Verify Secrets**: Ensure `SUPABASE_DATABASE_URL` is set in repository secrets
3. **Check Cron Schedule**: Verify the cron expression in the workflow file

### Workflow Failed

1. **Check Error Logs**: Click on the failed run and read the error message
2. **Common Issues**:
   - Database connection timeout
   - Aggregator API is down
   - Out of storage quota

### Data Not Being Saved

1. **Verify Database URL**: Check that `SUPABASE_DATABASE_URL` is correct
2. **Check Write Permissions**: Ensure the database user has INSERT permissions
3. **Check Tables Exist**: Verify `collection_runs` and `price_history` tables are created

## Manual Testing

To test the aggregator collection locally:

```bash
cd backend
source venv/bin/activate

# Test with local database
python scripts/run_task.py aggregate

# Or test price verification
python scripts/verify_aggregator.py
```

## Performance Baseline

For reference, a healthy aggregator collection run should:
- **Duration**: 15-45 seconds (depends on network)
- **Items**: ~17,000 items collected
- **Errors**: < 100 errors (out of 17k = <1% error rate)
- **Database**: Write ~17,000 price records

## Monitoring Schedule

Recommended monitoring cadence:
- **Daily**: Quick check that runs are appearing and succeeding
- **Weekly**: Review total data points and error trends
- **Monthly**: Analyze data collection completeness and plan any maintenance

## Contact & Support

If workflows are consistently failing:
1. Check the detailed logs in GitHub Actions
2. Review the Supabase database for connection issues
3. Verify all secrets are properly configured
