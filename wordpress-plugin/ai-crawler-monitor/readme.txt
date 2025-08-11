=== AI Crawler Monitor ===
Contributors: contestra
Tags: ai, seo, chatgpt, perplexity, claude, bot tracking, analytics
Requires at least: 5.0
Tested up to: 6.4
Stable tag: 1.0.0
Requires PHP: 7.2


Track AI bot traffic (ChatGPT, Perplexity, Claude) visiting your WordPress site and monitor when AI systems access your content.

== Description ==

AI Crawler Monitor tracks when AI bots visit your WordPress site, including:

* **ChatGPT-User** - When ChatGPT users ask about your content
* **Perplexity-User** - When Perplexity searches reference your site
* **ClaudeBot** - When Claude systems index your content
* **GPTBot** - OpenAI's training crawler
* **Google, Bing, Meta** AI crawlers
* And many more AI systems

= Key Features =

* Real-time bot detection (server-side, catches all bots)
* Distinguishes between indexing, training, and on-demand bots
* Sends data to your AI Ranker monitoring dashboard
* Non-blocking - doesn't slow down your site
* Works with Cloudflare and other CDNs
* No JavaScript required - catches all bot traffic

= How It Works =

1. Detects AI bots by analyzing User-Agent headers server-side
2. Captures request details (path, IP, timestamp)
3. Sends data asynchronously to your monitoring endpoint
4. View aggregated statistics in your AI Ranker dashboard

== Installation ==

1. Upload the `ai-crawler-monitor` folder to `/wp-content/plugins/`
2. Activate the plugin through the 'Plugins' menu in WordPress
3. Go to Settings > AI Crawler Monitor
4. Just click "Save Changes" - it's pre-configured with Contestra's data collection service!
5. Your bot traffic is now being tracked and analyzed

= Quick Start =

* **No server setup required** - Uses Contestra's data collection service
* **Pre-configured** - Works immediately after activation
* **Dashboard Access** - Contact Contestra for reports (client portal coming soon)

= Requirements =

* WordPress 5.0 or higher
* PHP 7.2 or higher
* Internet connection (to send data to monitoring service)

== Frequently Asked Questions ==

= Do I need to modify my theme? =

No, the plugin works automatically once activated. No theme modifications needed.

= Will this slow down my site? =

No, data is sent asynchronously with a 1-second timeout. Your pages load normally.

= What if my monitoring server is down? =

The plugin fails silently - your site continues working normally even if the monitoring endpoint is unavailable.

= Can I track all traffic, not just bots? =

Yes, there's an option to track all requests, but this generates a lot of data.

= Does this work with caching plugins? =

Yes, but cached pages won't trigger tracking. Only uncached requests are tracked.

= Does this work with Cloudflare? =

Yes, the plugin correctly detects the real visitor IP even behind Cloudflare.

== Configuration ==

= API Endpoint =

The plugin comes pre-configured with Contestra's data collection service:
* **Default**: `https://ai-ranker.fly.dev/api/crawler/ingest/generic` (Recommended)
* **Self-hosted**: Change to your own server if desired
* **Reports**: Contact support@contestra.com for your bot traffic analysis
* **Client Portal**: Individual dashboards coming soon!

= Enable Tracking =

Toggle to enable/disable bot tracking without deactivating the plugin.

= Track All Traffic =

Enable to track all requests, not just AI bots. Warning: generates significant data.

== Screenshots ==

1. Settings page with statistics display
2. List of detected AI bots
3. Real-time monitoring dashboard (AI Ranker)

== Changelog ==

= 1.0.0 =
* Initial release
* Support for major AI crawlers (OpenAI, Anthropic, Perplexity, Meta, Google)
* Non-blocking data transmission
* Admin settings page with statistics
* Cloudflare compatibility

== Privacy Notice ==

This plugin sends bot visitor data to the configured monitoring endpoint:
* IP addresses (for bot verification)
* User agent strings
* Requested URLs
* Timestamps

**Default Service**: Data is sent to Contestra's AI Ranker service (https://ai-ranker.fly.dev) by default.
**Self-Hosting**: You can change the endpoint to your own server for complete data control.
**Bot Traffic Only**: By default, only AI bot traffic is tracked, not regular human visitors.

== Technical Details ==

The plugin hooks into WordPress's `init` action to analyze requests before page rendering. It:

1. Extracts request headers (User-Agent, IP, path)
2. Checks User-Agent against known AI bot signatures
3. Sends data via `wp_remote_post()` with `blocking => false`
4. Uses 1-second timeout to prevent delays

= Known AI Bots Detected =

* OpenAI: ChatGPT-User, OAI-SearchBot, GPTBot
* Perplexity: PerplexityBot, Perplexity-User
* Anthropic: ClaudeBot, Claude-User
* Meta: meta-externalagent, meta-externalfetcher
* Google: Googlebot, Google-Extended
* Microsoft: bingbot
* Others: YouBot, cohere-ai
