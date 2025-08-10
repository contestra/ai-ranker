# airank.dejan.ai Screenshot Analysis

## Overview
These screenshots from airank.dejan.ai reveal a sophisticated AI brand visibility tracking system with multiple viewing modes, comprehensive tracking features, and detailed analytics. Here's what's important:

## 1. AI Visibility Tab (Screenshot 1)
### Key Features Observed:

#### Top 20 Entities Section (Left Table)
- **What it shows**: Entities that AIs associate with the AVEA brand
- **Important columns**:
  - Entity name (e.g., "4G", "SIM cards", "Mobile telecommunications")
  - Frequency (how often mentioned)
  - Avg Position (average rank when mentioned)
  - Weighted Score (combined metric)
- **Key insight**: Shows unexpected associations (telecom terms for a health brand), indicating potential brand confusion

#### Top 20 Brands Section (Right Table)
- **What it shows**: Competitor brands appearing for tracked phrases
- **Leading competitors**:
  - Garden of Life (22 mentions, 4.32 avg position)
  - Vital Proteins (14 mentions, 3.29 avg position)
  - Life Extension (9 mentions, 2.00 avg position)
- **AVEA's performance**: Not in top 10, indicating visibility challenge

#### Top Associations Bar Charts (Bottom)
- **Left chart**: Entity associations with AVEA brand
  - Shows telecommunications dominating (unintended)
  - AVEA brand name appears weakly
- **Right chart**: Brand associations for tracked phrases
  - Garden of Life dominates
  - Clear competitive landscape visualization
- **Weighted Score scale**: 0 to 0.5, with gradient coloring

## 2. Google Tab - Brand Rankings (Screenshot 2)
### Weekly Trend Visualizations

#### "Collagen activator" Tracking
- **Top performers**:
  - Neutrogena (consistent freq: 2)
  - Olay (freq: 2)
  - L'Oréal (freq: 2)
- **Trend patterns**: Lines show rank changes over 8-week period
- **Important**: Frequency shown in parentheses in legend
- **Date range**: Jul 13, 2025 to Aug 03, 2025

#### "Swiss NAD booster" Tracking
- **Market leaders**:
  - Elysium Health (freq: 4) - dramatic improvement from rank 9 to 1
  - Novos (freq: 3) - stable at top
  - Tru Niagen (freq: 3) - volatile ranking
- **Key pattern**: Elysium Health's rise coincides with others' decline

## 3. Google Tab Continued (Screenshots 3-4)
### Multiple Tracked Phrases Analysis

#### "best longevity supplements"
- **Dominant brands**:
  - Life Extension (freq: 4) - consistent #1
  - Thorne Research (freq: 4) - stable #2
  - NOW Foods (freq: 4) - stable #3
- **Competition**: Very stable rankings, hard to break into

#### "best swiss supplements"
- **Leaders**:
  - Burgerstein (freq: 4) - improving trend
  - Similasan (freq: 3) - declining
  - Doetsch Grether (freq: 3) - stable
- **Geographic advantage**: Swiss brands dominate Swiss-related queries

## 4. OpenAI Tab (Screenshots 5-6)
### "Your Brand" Section
Shows what OpenAI associates with AVEA brand over time

#### AVEA Brand Associations
- **Top associations** (with variance and frequency):
  - Telecommunications (4 var., freq: 3)
  - Mobile services (3 var., freq: 3)
  - Customer service (20 var., freq: 3)
- **Problem identified**: Brand confused with telecom company
- **Timeline**: Weekly tracking from Jul 13 to Aug 03, 2025

### "Your Phrases" Section
Shows which brands OpenAI returns for tracked phrases

#### "Collagen activator" Results
- **Winners**:
  - Vital Proteins (1 var., freq: 4) - dominant #1
  - Garden of Life (1 var., freq: 4) - strong #2
  - Sports Research (freq: 4) - consistent presence
- **Volatility**: Significant rank changes week-to-week

#### "Swiss NAD booster" Results
- **Limited competition**:
  - Renue by Science (freq: 2)
  - Quicksilver Scientific (freq: 2)
- **Opportunity**: Less saturated market segment

## 5. Settings Tab (Screenshots 7-8)
### Configuration Options

#### Project Settings
- **Language**: English (dropdown available)
- **Location**: Global (can be country-specific)
- **Created**: 2025-07-15 15:14:37
- **Tabs**: General Settings | Project Sharing | Danger Zone

#### Tracked Domains Management
- **Current domain**: www.avea-life.com
- **Bulk import feature**: 
  - Text area for multiple domains
  - One domain per line
  - Examples provided (example.com, another-site.org, mywebsite.net)

#### Tracked Phrases Management
- **Current phrases**:
  - Collagen activator
  - Swiss NAD booster
  - best longevity supplements
  - best swiss supplements
  - vegan collagen
- **Bulk import**: Similar interface to domains
- **Examples given**: Cloud Storage, IT Support, Electric Cars

## Key Insights from Screenshots

### 1. Data Visualization Excellence
- **Multi-dimensional tracking**: Frequency, position, and time
- **Color coding**: Each brand/entity has consistent color across charts
- **Interactive elements**: Weekly view toggle, pagination

### 2. Competitive Intelligence
- **Clear competitor identification**: Know exactly who you're competing against
- **Trend analysis**: See who's gaining/losing visibility
- **Market gaps**: Identify underserved tracked phrases

### 3. Problem Detection
- **Brand confusion**: AVEA associated with telecom instead of health
- **Low visibility**: Not appearing in top results for target phrases
- **Competitive dominance**: Established brands controlling key terms

### 4. Strategic Features
- **Canonical entity grouping**: Handles brand variations
- **Multi-model comparison**: OpenAI vs Google differences
- **Bulk management**: Efficient phrase/domain tracking

### 5. Time-Series Analysis
- **8-week windows**: Enough data for trend identification
- **Weekly granularity**: Captures rapid changes
- **Frequency tracking**: Shows consistency vs. one-time mentions

## Implementation Priorities Based on Screenshots

### Must-Have Features
1. **Tracked phrases system** - Core to E→B testing
2. **Weekly trend charts** - Essential for monitoring
3. **Top 20 tables** - Key competitive intelligence
4. **Weighted score calculation** - Executive metric
5. **Multi-tab interface** - Model comparison

### High-Value Additions
1. **Canonical entity toggle** - Reduces noise
2. **Bulk import interfaces** - Operational efficiency
3. **Bar chart visualizations** - Quick insights
4. **Frequency in parentheses** - Context in legends
5. **Domain tracking** - Brand monitoring

### Advanced Features
1. **Variance tracking** - Shows result stability
2. **Position history** - Detailed rank changes
3. **Project sharing** - Team collaboration
4. **Location filtering** - Geographic analysis
5. **Danger zone** - Project management

## Technical Implementation Notes

### Chart Requirements
- **Library needed**: Recharts or similar for line charts
- **Data structure**: Time-series with multiple entities
- **Interactivity**: Hover tooltips, clickable legends
- **Responsive**: Charts must scale properly

### Data Model Insights
- **Granularity**: Weekly aggregations required
- **Relationships**: Brand → Phrases → Results → Time
- **Metrics**: Frequency, Position, Weighted Score
- **History**: Minimum 8 weeks retention

### UI/UX Patterns
- **Consistent navigation**: Left sidebar for project selection
- **Tab organization**: Logical grouping of features
- **Visual hierarchy**: Tables, charts, settings in order
- **Color consistency**: Same colors across all visualizations
- **Toggle controls**: Weekly view checkboxes

## Competitive Advantages Revealed

### 1. BEEB Methodology
The screenshots confirm the Brand-Entity Embedding Benchmark approach:
- **E→B**: "Your Phrases" tracks which brands appear
- **B→E**: "Your Brand" tracks what's associated with you

### 2. Multi-Model Intelligence
Different models return different results:
- **Google**: More stable, established brands
- **OpenAI**: More volatile, newer brands can appear

### 3. Actionable Insights
The system clearly shows:
- **Where you rank**: Exact position tracking
- **Who beats you**: Specific competitor identification
- **What's associated**: Entity confusion detection
- **How to improve**: Gap identification for optimization

This screenshot analysis confirms that airank.dejan.ai is a comprehensive brand visibility platform that goes far beyond simple mention tracking, providing deep competitive intelligence and strategic insights for brand positioning in AI models.