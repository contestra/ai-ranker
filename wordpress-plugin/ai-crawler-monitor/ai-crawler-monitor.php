<?php
/**
 * Plugin Name: AI Crawler Monitor
 * Plugin URI: https://github.com/contestra/ai-crawler-monitor
 * Description: Tracks AI bot traffic (ChatGPT, Perplexity, Claude, etc.) and sends data to your AI Ranker monitoring dashboard
 * Version: 1.0.0
 * Author: Contestra
 * License: MIT
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Define plugin constants
define('AICM_VERSION', '1.0.0');
define('AICM_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('AICM_PLUGIN_URL', plugin_dir_url(__FILE__));

// Main plugin class
class AI_Crawler_Monitor {
    
    private $api_endpoint;
    private $enabled;
    private $known_bots = [
        // OpenAI
        'ChatGPT-User' => ['provider' => 'openai', 'type' => 'on_demand'],
        'OAI-SearchBot' => ['provider' => 'openai', 'type' => 'indexing'],
        'GPTBot' => ['provider' => 'openai', 'type' => 'training'],
        
        // Perplexity
        'PerplexityBot' => ['provider' => 'perplexity', 'type' => 'indexing'],
        'Perplexity-User' => ['provider' => 'perplexity', 'type' => 'on_demand'],
        
        // Anthropic
        'ClaudeBot' => ['provider' => 'anthropic', 'type' => 'training'],
        'Claude-User' => ['provider' => 'anthropic', 'type' => 'on_demand'],
        'anthropic-ai' => ['provider' => 'anthropic', 'type' => 'on_demand'],
        
        // Meta
        'meta-externalagent' => ['provider' => 'meta', 'type' => 'indexing'],
        'meta-externalfetcher' => ['provider' => 'meta', 'type' => 'on_demand'],
        
        // Google
        'Googlebot' => ['provider' => 'google', 'type' => 'indexing'],
        'Google-Extended' => ['provider' => 'google', 'type' => 'training'],
        
        // Microsoft
        'bingbot' => ['provider' => 'microsoft', 'type' => 'indexing'],
        
        // Others
        'YouBot' => ['provider' => 'youbot', 'type' => 'indexing'],
        'cohere-ai' => ['provider' => 'cohere', 'type' => 'training'],
    ];
    
    public function __construct() {
        // Load settings
        $this->api_endpoint = get_option('aicm_api_endpoint', 'https://ai-ranker.fly.dev/api/crawler/v2/ingest/generic');
        $this->enabled = get_option('aicm_enabled', true);
        
        // Hook into WordPress
        add_action('init', [$this, 'track_request'], 1);
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_init', [$this, 'register_settings']);
        
        // Add admin notices
        add_action('admin_notices', [$this, 'admin_notices']);
    }
    
    /**
     * Track incoming requests and send bot data to monitoring API
     */
    public function track_request() {
        if (!$this->enabled) {
            return;
        }
        
        // Get request data
        $user_agent = isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '';
        $client_ip = $this->get_client_ip();
        $path = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '/';
        $method = isset($_SERVER['REQUEST_METHOD']) ? $_SERVER['REQUEST_METHOD'] : 'GET';
        $referrer = isset($_SERVER['HTTP_REFERER']) ? $_SERVER['HTTP_REFERER'] : '';
        
        // Check if it's a bot
        $bot_info = $this->detect_bot($user_agent);
        
        // Only send data if it's a bot or if tracking all traffic
        if ($bot_info || get_option('aicm_track_all', false)) {
            // Get domain without protocol
            $site_url = get_site_url();
            $parsed_url = parse_url($site_url);
            $domain = $parsed_url['host'];
            
            // Remove www. if present
            $domain = preg_replace('/^www\./', '', $domain);
            
            $this->send_to_monitor([
                'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
                'domain' => $domain,  // Add domain to identify source
                'method' => $method,
                'path' => $path,
                'status' => 200, // WordPress will return 200 if we're here
                'user_agent' => $user_agent,
                'client_ip' => $client_ip,
                'provider' => $bot_info ? $bot_info['provider'] : 'unknown',
                'metadata' => [
                    'referrer' => $referrer,
                    'wordpress_site' => $site_url,
                    'bot_type' => $bot_info ? $bot_info['type'] : null,
                    'is_bot' => $bot_info !== false,
                    'plugin_version' => AICM_VERSION
                ]
            ]);
        }
    }
    
    /**
     * Detect if user agent is a known AI bot
     */
    private function detect_bot($user_agent) {
        if (empty($user_agent)) {
            return false;
        }
        
        foreach ($this->known_bots as $bot_signature => $bot_data) {
            if (stripos($user_agent, $bot_signature) !== false) {
                return $bot_data;
            }
        }
        
        return false;
    }
    
    /**
     * Get client IP address
     */
    private function get_client_ip() {
        // Check for Cloudflare
        if (!empty($_SERVER['HTTP_CF_CONNECTING_IP'])) {
            return $_SERVER['HTTP_CF_CONNECTING_IP'];
        }
        
        // Check for proxy headers
        $headers = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CLIENT_IP',
        ];
        
        foreach ($headers as $header) {
            if (!empty($_SERVER[$header])) {
                $ips = explode(',', $_SERVER[$header]);
                return trim($ips[0]);
            }
        }
        
        return isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '';
    }
    
    /**
     * Send data to monitoring API
     */
    private function send_to_monitor($data) {
        // Don't block page load - use non-blocking request
        $args = [
            'body' => json_encode($data),
            'headers' => [
                'Content-Type' => 'application/json',
            ],
            'timeout' => 1, // Short timeout
            'blocking' => false, // Non-blocking
            'sslverify' => false, // Allow self-signed certs for local dev
        ];
        
        wp_remote_post($this->api_endpoint, $args);
    }
    
    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        add_options_page(
            'AI Crawler Monitor',
            'AI Crawler Monitor',
            'manage_options',
            'ai-crawler-monitor',
            [$this, 'settings_page']
        );
    }
    
    /**
     * Register plugin settings
     */
    public function register_settings() {
        register_setting('aicm_settings', 'aicm_enabled');
        register_setting('aicm_settings', 'aicm_api_endpoint');
        register_setting('aicm_settings', 'aicm_track_all');
    }
    
    /**
     * Settings page HTML
     */
    public function settings_page() {
        // Get current stats
        $stats = $this->get_stats();
        ?>
        <div class="wrap">
            <h1>AI Crawler Monitor Settings</h1>
            
            <?php if ($stats): ?>
            <div class="card" style="max-width: 600px; margin: 20px 0;">
                <h2>Current Statistics</h2>
                <p><strong>Total Hits:</strong> <?php echo esc_html($stats['total_hits']); ?></p>
                <p><strong>Bot Hits:</strong> <?php echo esc_html($stats['bot_hits']); ?> (<?php echo esc_html(round($stats['bot_percentage'], 1)); ?>%)</p>
                <p><strong>On-Demand Queries:</strong> <?php echo esc_html($stats['on_demand_hits']); ?></p>
                <p><strong>Top Bots:</strong></p>
                <ul>
                    <?php foreach (array_slice($stats['top_bots'], 0, 5) as $bot => $count): ?>
                        <li><?php echo esc_html($bot); ?>: <?php echo esc_html($count); ?> hits</li>
                    <?php endforeach; ?>
                </ul>
            </div>
            <?php endif; ?>
            
            <form method="post" action="options.php">
                <?php settings_fields('aicm_settings'); ?>
                
                <table class="form-table">
                    <tr>
                        <th scope="row">Enable Tracking</th>
                        <td>
                            <label>
                                <input type="checkbox" name="aicm_enabled" value="1" <?php checked(get_option('aicm_enabled', true)); ?> />
                                Track AI bot traffic
                            </label>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">API Endpoint</th>
                        <td>
                            <input type="text" name="aicm_api_endpoint" value="<?php echo esc_attr(get_option('aicm_api_endpoint', 'https://ai-ranker.fly.dev/api/crawler/v2/ingest/generic')); ?>" class="regular-text" />
                            <p class="description">Default: Contestra's AI Ranker cloud service (https://ai-ranker.fly.dev)</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Track All Traffic</th>
                        <td>
                            <label>
                                <input type="checkbox" name="aicm_track_all" value="1" <?php checked(get_option('aicm_track_all', false)); ?> />
                                Track all requests (not just bots)
                            </label>
                            <p class="description">Warning: This will send a lot of data</p>
                        </td>
                    </tr>
                </table>
                
                <?php submit_button(); ?>
            </form>
            
            <div class="card" style="max-width: 600px; margin-top: 30px;">
                <h2>Detected AI Bots</h2>
                <p>This plugin detects the following AI bots:</p>
                <ul style="column-count: 2;">
                    <?php foreach ($this->known_bots as $bot => $info): ?>
                        <li><?php echo esc_html($bot); ?> (<?php echo esc_html($info['provider']); ?>)</li>
                    <?php endforeach; ?>
                </ul>
            </div>
            
            <div class="card" style="max-width: 600px; margin-top: 20px;">
                <h2>Setup Instructions</h2>
                <ol>
                    <li>The plugin is pre-configured to use Contestra's data collection service</li>
                    <li>Just enable tracking and save settings - no server setup needed!</li>
                    <li>Your bot traffic data is being collected and analyzed</li>
                    <li>Contact Contestra for reports and dashboard access (coming soon)</li>
                </ol>
                <p><strong>Note:</strong> This plugin sends data asynchronously and won't slow down your site.</p>
                <p><strong>Dashboard Access:</strong> Currently for Contestra internal use. Client portal with individual dashboards coming soon!</p>
                <p><strong>Need Reports?</strong> Contact support@contestra.com for your bot traffic analysis.</p>
            </div>
        </div>
        <?php
    }
    
    /**
     * Get stats from monitoring API
     */
    private function get_stats() {
        $api_base = str_replace('/ingest/generic', '', $this->api_endpoint);
        $stats_url = $api_base . '/monitor/stats';
        
        $response = wp_remote_get($stats_url, [
            'timeout' => 5,
            'sslverify' => false,
        ]);
        
        if (is_wp_error($response)) {
            return false;
        }
        
        $body = wp_remote_retrieve_body($response);
        return json_decode($body, true);
    }
    
    /**
     * Show admin notices
     */
    public function admin_notices() {
        if (!$this->enabled) {
            return;
        }
        
        // Only show on plugin settings page
        $screen = get_current_screen();
        if ($screen->id !== 'settings_page_ai-crawler-monitor') {
            return;
        }
        
        // Test connection
        $api_base = str_replace('/ingest/generic', '', $this->api_endpoint);
        $test_url = str_replace('/api/crawler', '', $api_base);
        
        $response = wp_remote_get($test_url, [
            'timeout' => 2,
            'sslverify' => false,
        ]);
        
        if (is_wp_error($response)) {
            ?>
            <div class="notice notice-warning">
                <p><strong>AI Crawler Monitor:</strong> Cannot connect to monitoring API at <?php echo esc_html($this->api_endpoint); ?>. Please check your settings.</p>
            </div>
            <?php
        }
    }
}

// Initialize plugin
new AI_Crawler_Monitor();

// Activation hook
register_activation_hook(__FILE__, function() {
    // Set default options
    if (get_option('aicm_api_endpoint') === false) {
        update_option('aicm_api_endpoint', 'https://ai-ranker.fly.dev/api/crawler/v2/ingest/generic');
    }
    if (get_option('aicm_enabled') === false) {
        update_option('aicm_enabled', true);
    }
});