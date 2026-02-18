# Usage Guide

Comprehensive guide for using Telegram Panel.

## Getting Started

### Initial Setup

1. Install dependencies and configure environment as described in main README
2. Start the bot by running `python main.py`
3. Send `/start` command to the bot in Telegram
4. Verify you receive the main menu

### First Account Addition

1. Click "Account Management" from main menu
2. Select "Add Account"
3. Enter phone number in international format (e.g., +1234567890)
4. Enter verification code received via Telegram
5. If 2FA is enabled, enter password when prompted
6. Account will be automatically saved and activated

## Account Management

### Adding Accounts

Navigate to Account Management > Add Account and follow the authentication flow.

### Listing Accounts

Select "List Accounts" to view all configured accounts with their status.

### Checking Report Status

Use "Check Report Status" to verify if any accounts have active reports that may limit functionality.

### Updating Groups

Select "Update Groups" to refresh the list of groups/channels for all accounts. This operation may take time depending on the number of accounts.

## Individual Operations

Individual operations allow you to perform actions using a single selected account.

### Reaction

1. Select "Individual" from main menu
2. Choose "Reaction"
3. Select account to use
4. Enter Telegram message link
5. Select reaction emoji
6. Reaction will be applied

### Poll Voting

1. Select "Individual" > "Poll"
2. Select account
3. Enter poll message link
4. Select poll option
5. Vote will be cast

### Join Group/Channel

1. Select "Individual" > "Join"
2. Select account
3. Enter group/channel link or username
4. Account will join the group/channel

### Leave Group/Channel

1. Select "Individual" > "Leave"
2. Select account
3. Enter group/channel link or username
4. Account will leave the group/channel

### Block User

1. Select "Individual" > "Block"
2. Select account
3. Enter username or user ID
4. User will be blocked

### Send Private Message

1. Select "Individual" > "Send PV"
2. Select account
3. Enter username or user ID
4. Enter message text
5. Message will be sent

### Comment on Message

1. Select "Individual" > "Comment"
2. Select account
3. Enter message link
4. Enter comment text
5. Comment will be posted

## Bulk Operations

Bulk operations execute actions across multiple accounts simultaneously.

### Bulk Reaction

1. Select "Bulk" > "Reaction"
2. Choose number of accounts to use
3. Enter message link
4. Select reaction emoji
5. Reaction will be applied by selected accounts

### Bulk Poll Voting

1. Select "Bulk" > "Poll"
2. Choose number of accounts
3. Enter poll message link
4. Select poll option
5. Votes will be cast by selected accounts

### Bulk Join

1. Select "Bulk" > "Join"
2. Choose number of accounts
3. Enter group/channel link
4. Selected accounts will join

### Bulk Leave

1. Select "Bulk" > "Leave"
2. Choose number of accounts
3. Enter group/channel link
4. Selected accounts will leave

### Bulk Block

1. Select "Bulk" > "Block"
2. Choose number of accounts
3. Enter username or user ID
4. User will be blocked by selected accounts

### Bulk Send Private Message

1. Select "Bulk" > "Send PV"
2. Choose number of accounts
3. Enter username or user ID
4. Enter message text
5. Message will be sent from selected accounts

### Bulk Comment

1. Select "Bulk" > "Comment"
2. Choose number of accounts
3. Enter message link
4. Enter comment text
5. Comments will be posted by selected accounts

## Monitor Mode

Monitor mode enables automatic message filtering and forwarding based on keywords.

### Setting Up Monitoring

1. Configure CHANNEL_ID in `.env` file
2. Select "Monitor Mode" from main menu
3. Add keywords to monitor
4. Configure target groups if needed
5. Monitoring will start automatically

### Adding Keywords

1. Select "Monitor Mode" > "Add Keyword"
2. Enter keyword to monitor
3. Keyword will be added to monitoring list

### Removing Keywords

1. Select "Monitor Mode" > "Remove Keyword"
2. Select keyword from list
3. Keyword will be removed

### Managing Ignore List

1. Select "Monitor Mode" > "Ignore User"
2. Enter username or user ID
3. User will be added to ignore list
4. Messages from ignored users will not be forwarded

### Viewing Configuration

- "Show Groups": Display all monitored groups
- "Show Keywords": Display all monitoring keywords
- "Show Ignores": Display ignored users list

### Updating Groups

Select "Update Groups" to refresh the list of groups being monitored. This ensures new groups are included in monitoring.

## Report Status

View statistics and account status information.

### Bot Statistics

Select "Report Status" > "Show Stats" to view:
- Total number of accounts
- Active accounts count
- Inactive accounts count
- System status

### Groups Per Account

Select "Groups Per Account" to view the number of groups/channels each account is a member of.

### Keyword Overview

Select "Show Keywords" to view all configured monitoring keywords.

## Link Formats

The system supports various Telegram link formats:

### Public Channels/Groups
```
https://t.me/username/123
t.me/username/123
```

### Private Channels/Groups
```
https://t.me/c/1234567890/123
t.me/c/1234567890/123
```

### Direct Entity References
- Username: `@username`
- Numeric ID: `123456789`
- Channel ID: `-1001234567890`

## Best Practices

### Account Management

- Add accounts gradually to avoid rate limiting
- Monitor account status regularly
- Remove revoked sessions promptly
- Keep 2FA enabled for security

### Bulk Operations

- Start with small account counts to test
- Monitor for rate limiting issues
- Use appropriate delays between operations
- Check operation results before scaling up

### Monitoring

- Use specific keywords to reduce false positives
- Regularly update ignore list
- Monitor forwarded messages for relevance
- Adjust keyword list based on results

### Security

- Never share session files
- Use strong 2FA passwords
- Regularly rotate credentials
- Monitor for unauthorized access

## Error Handling

### Common Errors

**Session Revoked**
- Account session has been terminated
- Remove account and re-add
- Check Telegram security settings

**Flood Wait**
- Too many requests in short time
- System automatically handles delays
- Wait for operation to complete

**Invalid Link**
- Link format is incorrect
- Verify link is complete and valid
- Use supported link formats

**Account Not Found**
- Account may not be active
- Check account status
- Re-authenticate if needed

### Error Recovery

The system includes automatic error recovery:
- Retry logic for transient errors
- Automatic session cleanup
- Graceful degradation on failures
- Detailed error logging

## Troubleshooting

### Bot Not Responding

1. Check bot is running: `python main.py`
2. Verify bot token is correct
3. Check logs in `logs/bot.log`
4. Restart bot if needed

### Account Authentication Fails

1. Verify phone number format
2. Check verification code is entered promptly
3. Verify 2FA password if enabled
4. Try re-adding account

### Operations Not Working

1. Check account status
2. Verify account has necessary permissions
3. Check for rate limiting
4. Review error logs

### Monitoring Not Forwarding

1. Verify CHANNEL_ID is configured
2. Check keywords are added
3. Verify target groups are configured
4. Check account has access to groups

## Advanced Usage

### Custom Configuration

Edit `config.json` directly for advanced configuration:
- Modify target groups list
- Adjust batch sizes
- Configure rate limiting parameters

### Log Analysis

Review `logs/bot.log` for:
- Operation execution details
- Error diagnostics
- Performance metrics
- Security events

### Session Management

Session files are stored in project root:
- Format: `{phone_number}.session`
- Backup session files regularly
- Never commit to version control
- Keep secure and encrypted if possible

