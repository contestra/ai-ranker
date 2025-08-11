# AI Crawler Monitor - WordPress Plugin

A WordPress plugin that tracks AI bot traffic (ChatGPT, Perplexity, Claude, etc.) and sends data to your AI Ranker monitoring dashboard.

## Features

- **Server-side bot detection** - Catches all AI bots (they don't need to execute JavaScript)
- **Real-time tracking** - Sends data immediately to your monitoring dashboard
- **Non-blocking** - Uses asynchronous requests, won't slow down your site
- **CDN compatible** - Works with Cloudflare and other CDNs
- **Privacy focused** - Only tracks bots by default, not regular visitors

## Installation

### Method 1: Direct Upload
1. Download the `ai-crawler-monitor` folder
2. Upload to your WordPress `/wp-content/plugins/` directory
3. Activate the plugin in WordPress admin

### Method 2: ZIP Upload
1. Zip the `ai-crawler-monitor` folder
2. Go to WordPress Admin > Plugins > Add New > Upload Plugin
3. Upload the ZIP file and activate

## Configuration

### Quick Start (Using Contestra's Data Collection Service)
1. **Install and activate** the plugin
2. Go to **Settings > AI Crawler Monitor**
3. **Just click Save** - it's pre-configured!
4. Your bot traffic data is now being collected

### Default Configuration
The plugin comes pre-configured with Contestra's AI bot data collection service:
- **Default Endpoint**: `https://ai-ranker.fly.dev/api/crawler/v2/ingest/generic`
- **No server setup required** - works immediately
- **Free data collection** for WordPress sites

**Note**: Dashboard access is currently available for Contestra internal use only. Client portal with individual dashboards coming soon!

### Self-Hosting (Optional)
If you prefer to run your own monitoring server:
1. Deploy the AI Ranker backend to your server
2. Change the API Endpoint in settings
3. Example: `https://your-server.com/api/crawler/v2/ingest/generic`

## How It Works

```php
// The plugin detects bots by checking User-Agent headers
'ChatGPT-User' => ['provider' => 'openai', 'type' => 'on_demand']
'PerplexityBot' => ['provider' => 'perplexity', 'type' => 'indexing']
'ClaudeBot' => ['provider' => 'anthropic', 'type' => 'training']

// Sends data asynchronously to your monitoring endpoint
wp_remote_post($endpoint, [
    'blocking' => false,  // Non-blocking
    'timeout' => 1,       // 1 second timeout
    'body' => json_encode($bot_data)
]);
```

## Detected AI Bots

### OpenAI
- `ChatGPT-User` - Live queries from ChatGPT users
- `OAI-SearchBot` - ChatGPT Search indexing
- `GPTBot` - Training data collection

### Perplexity
- `PerplexityBot` - Search indexing
- `Perplexity-User` - Live user queries

### Anthropic
- `ClaudeBot` - Training and indexing
- `Claude-User` - Live queries from Claude users

### Others
- `Googlebot`, `Google-Extended` (Google)
- `meta-externalagent`, `meta-externalfetcher` (Meta)
- `bingbot` (Microsoft)
- `YouBot`, `cohere-ai`

## Requirements

- WordPress 5.0+
- PHP 7.2+
- No server required (uses Contestra's cloud service by default)

## Performance

The plugin is designed to have minimal impact:
- Runs early in WordPress lifecycle (priority 1)
- Non-blocking HTTP requests
- 1-second timeout on API calls
- Fails silently if monitoring server is down

## Privacy Considerations

The plugin sends to your monitoring server:
- User-Agent strings
- IP addresses (for bot verification)
- Requested URLs
- Timestamps
- Referrer URLs

By default, only AI bot traffic is tracked, not regular visitors.

## Troubleshooting

### Not seeing any data?
1. Make sure the plugin is activated and enabled in settings
2. Check that bots are actually visiting your site
3. Contact Contestra for dashboard access and reports
4. For technical issues, check WordPress debug log

### Need your bot traffic report?
Contact Contestra at support@contestra.com for:
- Bot traffic analysis reports
- Custom dashboard access (when available)
- Enterprise solutions

### Getting connection errors?
- For local development, the plugin disables SSL verification
- Make sure your firewall allows outbound connections
- Check your monitoring server is accessible from WordPress

### Works with caching?
- The plugin only tracks uncached requests
- Page cache bypass for bots is recommended
- Consider adding bot User-Agents to cache bypass rules

## Advanced Configuration

### Track all traffic (not just bots)
```php
update_option('aicm_track_all', true);
```

### Change API endpoint programmatically
```php
// Default Contestra cloud service
update_option('aicm_api_endpoint', 'https://ai-ranker.fly.dev/api/crawler/v2/ingest/generic');

// Or your own server
update_option('aicm_api_endpoint', 'https://your-server.com/api/crawler/v2/ingest/generic');
```

### Disable tracking temporarily
```php
update_option('aicm_enabled', false);
```

## Development

### Adding new bot signatures
Edit the `$known_bots` array in the main plugin file:
```php
private $known_bots = [
    'NewBot' => ['provider' => 'company', 'type' => 'indexing'],
    // Add more...
];
```

### Customizing data sent
Modify the `track_request()` method to add custom metadata.

## License

Copyright Contestra