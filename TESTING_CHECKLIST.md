# ConfigStream Daemon Testing Checklist

## Pre-Launch Checks

- [ ] All dependencies installed: `pip install -e .`
- [ ] Data directory exists or can be created
- [ ] No process using port 8080
- [ ] Can access localhost

## Starting the Daemon

1. Start daemon:
   ```bash
   configstream daemon --interval 2 --port 8080
   ```

2. Verify startup output shows:
   - [ ] Data directory path
   - [ ] Test interval
   - [ ] Web dashboard URL
   - [ ] "Scheduler started" message
   - [ ] "Starting web dashboard" message

3. Check initial test cycle:
   - [ ] Logs show "Starting scheduled test cycle"
   - [ ] Logs show VPN testing progress
   - [ ] Logs show "Test cycle completed successfully"
   - [ ] Statistics are logged (total/successful/failed)

## Data Files

Check `./data/` directory:

- [ ] `current_results.json` exists
- [ ] File contains valid JSON
- [ ] Has timestamp, nodes array
- [ ] Nodes have expected fields (protocol, ip, port, ping_ms, etc.)

- [ ] `history.jsonl` exists
- [ ] Contains one JSON object per line
- [ ] Each line is valid JSON

## Web Dashboard

Visit http://localhost:8080:

### Main Page
- [ ] Dashboard loads without errors
- [ ] Header shows "ConfigStream Dashboard"
- [ ] Last update timestamp displayed
- [ ] Auto-refresh indicator pulsing

### Statistics Cards
- [ ] Total Nodes shows correct count
- [ ] Successful shows correct count
- [ ] Average Ping shows value in ms
- [ ] Countries shows count

### Filters
- [ ] Protocol dropdown populated
- [ ] Country dropdown populated
- [ ] All filter inputs work
- [ ] "Apply Filters" button filters table
- [ ] "Clear" button resets filters

### Table
- [ ] Shows all nodes by default
- [ ] Columns: Protocol, Country, City, IP:Port, Ping, Organization, Status
- [ ] Ping values color-coded (green < 100ms, yellow < 300ms, red > 300ms)
- [ ] Failed nodes show "Failed" in red
- [ ] Blocked nodes show badge

### Export
- [ ] CSV export downloads file
- [ ] CSV contains all current data
- [ ] JSON export downloads file
- [ ] JSON is valid

## API Endpoints

Test each endpoint:

```bash
# Current results
curl http://localhost:8080/api/current

# With filters
curl "http://localhost:8080/api/current?protocol=vmess&max_ping=100"

# Statistics
curl http://localhost:8080/api/statistics

# History (last 24 hours)
curl "http://localhost:8080/api/history?hours=24"

# Export
curl http://localhost:8080/api/export/json -o test.json
curl http://localhost:8080/api/export/csv -o test.csv
```

Expected:
- [ ] All return 200 status
- [ ] JSON is valid
- [ ] Exports download correctly

## Scheduled Testing

Wait for next scheduled test (2 hours):

- [ ] Logs show "Starting scheduled test cycle"
- [ ] Test completes successfully
- [ ] `current_results.json` updated (check timestamp)
- [ ] New entry appended to `history.jsonl`
- [ ] Dashboard auto-refreshes with new data

## Graceful Shutdown

Press Ctrl+C:

- [ ] Shows "Shutting down gracefully..."
- [ ] Scheduler stops
- [ ] No errors during shutdown
- [ ] Process exits cleanly

## Error Handling

Test error scenarios:

1. Invalid data directory:
   ```bash
   configstream daemon --data-dir /invalid/path
   ```
   - [ ] Shows clear error message

2. Port already in use:
   ```bash
   # Start daemon twice on same port
   ```
   - [ ] Second instance shows port conflict error

3. Delete data files while running:
   ```bash
   rm data/current_results.json
   ```
   - [ ] Dashboard shows "No data available"
   - [ ] Next test cycle recreates files

## Performance

- [ ] Dashboard loads in < 2 seconds
- [ ] Table with 100+ nodes renders smoothly
- [ ] Filtering is instant
- [ ] No memory leaks over 24 hours
- [ ] CPU usage acceptable during testing

## Browser Compatibility

Test in multiple browsers:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari
- [ ] Edge

All should work identically.

## Sign-Off

- [ ] All checks passed
- [ ] No critical issues found
- [ ] Ready for production use

Tested by: ________________
Date: ________________