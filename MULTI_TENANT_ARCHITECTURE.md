# Multi-Tenant AI Crawler Monitor Architecture

## Overview

The AI Crawler Monitor has been redesigned to support multiple brands/domains with proper data separation and automatic technology detection.

## Key Improvements

### 1. Multi-Tenant Data Model
- **Domain Model**: Each brand can have multiple domains/subdomains
- **BotEvent Model**: All bot traffic is linked to specific domains and brands
- **PostgreSQL Storage**: Persistent storage instead of in-memory
- **Data Separation**: Each client only sees their own data

### 2. Domain Management

#### Adding Domains
Each brand can add multiple domains:
- **Primary Domain**: `avea-life.com`
- **Subdomains**: `insights.avea-life.com`, `blog.avea-life.com`
- **Multiple Sites**: Track different properties under one brand

#### Domain Validation
Automatic detection of:
- **Technology Stack**: WordPress, Shopify, Wix, custom, etc.
- **Trackability**: Whether server-side tracking is possible
- **Recommended Method**: WordPress plugin, Cloudflare Worker, etc.

### 3. Technology Detection

The system automatically detects:

#### ✅ Trackable Platforms
- **WordPress** (self-hosted) - Use plugin
- **Custom Sites** - Direct integration
- **Vercel** - Log drains
- **Netlify** - Log forwarding
- **Sites with Cloudflare** (if you control it) - Workers

#### ❌ Untrackable Platforms
- **Shopify** - No server access
- **Wix** - Closed platform
- **Squarespace** - No plugin support
- **WordPress.com** - Can't install plugins

### 4. WordPress Plugin Updates

The plugin now sends domain information:
```php
'domain' => 'avea-life.com',  // Identifies which site
'plugin_version' => '1.0.0'    // For compatibility
```

## API Endpoints

### Domain Management

#### Add Domain to Brand
```http
POST /api/domains/brands/{brand_id}/domains
{
  "url": "avea-life.com"
}
```

Response includes:
- Trackability status
- Detected technology
- Recommended tracking method

#### Validate Domain (without saving)
```http
POST /api/domains/validate?url=avea-life.com
```

Returns:
```json
{
  "domain": "avea-life.com",
  "is_trackable": false,
  "technology": ["shopify"],
  "messages": ["Shopify platform detected - cannot track server-side"],
  "recommendation": "Consider using a trackable subdomain (e.g., blog.yourdomain.com on WordPress)"
}
```

### Crawler Monitor V2

#### Domain-Specific Stats
```http
GET /api/crawler/v2/monitor/stats/avea-life.com
```

#### Brand Overview
```http
GET /api/crawler/v2/monitor/brand/{brand_id}/domains
```

Shows all domains for a brand with quick stats.

#### WebSocket (Real-time)
```
ws://localhost:8000/api/crawler/v2/ws/monitor/avea-life.com
```

Separate WebSocket channels per domain.

## Frontend Updates Needed

### Brand Settings Page
```jsx
// New Domain Management Section
<DomainManager brandId={brandId}>
  <DomainInput 
    placeholder="Enter domain (e.g., avea-life.com)"
    onValidate={validateDomain}
    showTechDetection={true}
  />
  
  <DomainList>
    {domains.map(domain => (
      <DomainCard
        key={domain.id}
        domain={domain}
        showStatus={domain.is_trackable}
        technology={domain.technology}
        botHits={domain.total_bot_hits}
      />
    ))}
  </DomainList>
</DomainManager>
```

### Crawler Monitor Dashboard
```jsx
// Domain selector at top
<DomainSelector 
  domains={brandDomains}
  selected={selectedDomain}
  onChange={setSelectedDomain}
/>

// Stats filtered by domain
<CrawlerStats domain={selectedDomain} />

// Events filtered by domain
<EventStream domain={selectedDomain} />
```

## Database Schema

```sql
-- Domains table
CREATE TABLE domains (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER REFERENCES brands(id),
    url VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100),
    is_trackable BOOLEAN DEFAULT true,
    technology VARCHAR(100),
    technology_details JSONB,
    tracking_method VARCHAR(50),
    validation_status VARCHAR(20),
    validation_message TEXT,
    total_bot_hits INTEGER DEFAULT 0,
    last_bot_hit TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bot events table
CREATE TABLE bot_events (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER REFERENCES domains(id),
    brand_id INTEGER REFERENCES brands(id),
    is_bot BOOLEAN,
    bot_name VARCHAR(100),
    bot_type VARCHAR(50),
    provider VARCHAR(50),
    method VARCHAR(10),
    path VARCHAR(500),
    status INTEGER,
    user_agent TEXT,
    client_ip VARCHAR(45),
    verified BOOLEAN,
    potential_spoof BOOLEAN,
    timestamp TIMESTAMP NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_bot_events_domain_timestamp ON bot_events(domain_id, timestamp DESC);
CREATE INDEX idx_bot_events_brand ON bot_events(brand_id);
CREATE INDEX idx_domains_brand ON domains(brand_id);
```

## Migration Path

### From V1 to V2

1. **Run Database Migrations**
```bash
cd backend
alembic upgrade head
```

2. **Update WordPress Plugins**
- New version sends domain info
- Backward compatible

3. **Switch API Endpoints**
- Old: `/api/crawler/ingest/generic`
- New: `/api/crawler/v2/ingest/generic`

4. **Update Frontend**
- Add domain management UI
- Update crawler monitor to filter by domain

## Example User Flow

### Setting Up Tracking

1. **User adds brand**: "AVEA Life"

2. **User adds domains**:
   - `avea-life.com` → ❌ Shopify detected, not trackable
   - `insights.avea-life.com` → ✅ WordPress detected, trackable
   - `content.avea-life.com` → ✅ Custom platform, trackable

3. **System provides guidance**:
   - For WordPress: "Install our plugin"
   - For Shopify: "Use a trackable subdomain instead"
   - For Custom: "Contact support for integration"

4. **User installs plugin** on WordPress sites

5. **Data flows**:
   - Bot visits site → Plugin detects → Sends to API with domain
   - API stores in PostgreSQL linked to correct domain/brand
   - Dashboard shows filtered data per domain

## Benefits

### For Users
- Track multiple properties under one brand
- See which domains get most AI bot traffic
- Automatic technology detection
- Clear guidance on what's trackable

### For Contestra
- Proper client data separation
- Scalable architecture
- Ready for client portal
- Better analytics per domain

### Technical
- PostgreSQL for persistence
- Proper foreign keys and relationships
- WebSocket channels per domain
- Efficient indexing

## Implementation Status

### ✅ Completed
1. **Backend**
   - Multi-tenant database models (Domain, BotEvent)
   - Domain validation service with technology detection
   - Crawler Monitor V2 API with domain separation
   - WebSocket support per domain
   - PostgreSQL storage

2. **Frontend**
   - CrawlerMonitorV2 component with integrated domain management
   - Domain input with automatic validation
   - Technology detection badges
   - Visual indicators for trackability
   - Domain selector for viewing stats
   - Real-time WebSocket updates per domain

3. **WordPress Plugin**
   - Updated to use V2 endpoint
   - Sends domain information with each request
   - Production endpoint configured

### 🚀 Ready for Testing

The multi-tenant crawler monitor is now fully integrated:
- Access the Crawler Monitor tab in the dashboard
- Add domains directly in the Crawler Monitor interface
- Each domain is automatically validated and technology detected
- Green badges = trackable (WordPress, custom)
- Red badges = not trackable (Shopify, Wix, etc.)
- Select any domain to view its specific bot traffic
- Real-time updates via WebSocket per domain

## Next Steps

1. **Database Migration**
   - Run Alembic migrations to create new tables
   - Command: `cd backend && alembic upgrade head`

2. **Enhanced Detection**
   - More platform signatures
   - JavaScript framework detection
   - CMS version detection

3. **Client Portal**
   - User authentication
   - Role-based access
   - Domain ownership verification

4. **Analytics**
   - Domain comparison charts
   - Cross-domain bot patterns
   - Technology-based insights