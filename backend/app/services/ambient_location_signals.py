"""
Ambient Location Signals (ALS) Builder
Provides ultra-minimal location context without brand contamination
"""

from typing import Dict, List
from datetime import datetime
import random
import pytz

class AmbientLocationSignalsBuilder:
    """
    Builds minimal ambient context blocks that make AI infer location
    without mentioning brands or products. Uses civic/government signals only.
    """
    
    # Country-specific ambient signals (civic, non-commercial)
    COUNTRY_SIGNALS = {
        'CH': {
            'timezone': 'Europe/Zurich',
            'utc_offset': '+01:00',  # Changes with DST
            'civic_phrases': [
                'ch.ch — "Führerausweis verlängern"',
                'admin.ch — "AHV-Nummer beantragen"',
                'ch.ch — "renouveler permis de conduire"',
                'sbb.ch Fahrplan — "Halbtax erneuern"',
                'post.ch — "Einschreiben verfolgen"'
            ],
            'formatting': [
                '8001 Zürich • +41 44 xxx xx xx • CHF 12.90',
                '3011 Bern • +41 31 xxx xx xx • CHF 89.50',
                '1200 Genève • +41 22 xxx xx xx • CHF 45.00'
            ],
            'weather_cities': ['Zürich', 'Bern', 'Geneva', 'Basel'],
            'agency_keywords': ['MeteoSchweiz', 'ESTV', 'BAG', 'SBB']
        },
        'DE': {
            'timezone': 'Europe/Berlin',
            'utc_offset': '+01:00',
            'civic_phrases': [
                'bund.de — "Führerschein verlängern"',
                'arbeitsagentur.de — "Arbeitslosengeld beantragen"',
                'deutsche-rentenversicherung.de — "Rentenkonto"',
                'elster.de — "Steuererklärung einreichen"',
                'bamf.de — "Aufenthaltstitel verlängern"'
            ],
            'formatting': [
                '10115 Berlin • +49 30 xxxx xxxx • 12,90 €',
                '80331 München • +49 89 xxxx xxxx • 45,50 €',
                '20095 Hamburg • +49 40 xxxx xxxx • 89,00 €'
            ],
            'weather_cities': ['Berlin', 'München', 'Hamburg', 'Frankfurt'],
            'agency_keywords': ['DWD', 'Finanzamt', 'BfArM', 'DB']
        },
        'US': {
            'timezone': 'America/New_York',
            'utc_offset': '-05:00',
            'civic_phrases': [
                'dmv.gov — "driver license renewal"',
                'irs.gov — "tax return status"',
                'ssa.gov — "social security benefits"',
                'usps.com — "change of address"',
                'usa.gov — "passport application"'
            ],
            'formatting': [
                'New York, NY 10001 • (212) xxx-xxxx • $12.99',
                'Los Angeles, CA 90001 • (213) xxx-xxxx • $45.50',
                'Chicago, IL 60601 • (312) xxx-xxxx • $89.00'
            ],
            'weather_cities': ['New York', 'Los Angeles', 'Chicago', 'Houston'],
            'agency_keywords': ['NOAA', 'IRS', 'DMV', 'USPS']
        },
        'GB': {
            'timezone': 'Europe/London',
            'utc_offset': '+00:00',
            'civic_phrases': [
                'gov.uk — "renew driving licence DVLA"',
                'nhs.uk — "book GP appointment"',
                'gov.uk — "council tax payment"',
                'gov.uk — "passport renewal"',
                'gov.uk — "universal credit application"'
            ],
            'formatting': [
                'London SW1A 1AA • 020 xxxx xxxx • £12.99',
                'Manchester M1 1AE • 0161 xxx xxxx • £45.50',
                'Birmingham B1 1BB • 0121 xxx xxxx • £89.00'
            ],
            'weather_cities': ['London', 'Manchester', 'Birmingham', 'Edinburgh'],
            'agency_keywords': ['Met Office', 'HMRC', 'DVLA', 'NHS']
        },
        'AE': {
            'timezone': 'Asia/Dubai',
            'utc_offset': '+04:00',
            'civic_phrases': [
                'u.ae — "Emirates ID renewal"',
                'rta.ae — "Salik recharge"',
                'mohap.gov.ae — "medical license"',
                'government.ae — "visa status"',
                'dewa.gov.ae — "bill payment"'
            ],
            'formatting': [
                'Dubai • +971 4 xxx xxxx • AED 49.00',
                'Abu Dhabi • +971 2 xxx xxxx • AED 125.00',
                'Sharjah • +971 6 xxx xxxx • AED 89.00'
            ],
            'weather_cities': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman'],
            'agency_keywords': ['NCM', 'RTA', 'DEWA', 'Etisalat']
        },
        'SG': {
            'timezone': 'Asia/Singapore',
            'utc_offset': '+08:00',
            'civic_phrases': [
                'singpass.gov.sg — "login"',
                'cpf.gov.sg — "contribution statement"',
                'ica.gov.sg — "passport renewal"',
                'mom.gov.sg — "work pass status"',
                'hdb.gov.sg — "BTO application"'
            ],
            'formatting': [
                'Singapore 238823 • +65 6xxx xxxx • S$12.90',
                'Singapore 018956 • +65 6xxx xxxx • S$45.50',
                'Singapore 608526 • +65 6xxx xxxx • S$89.00'
            ],
            'weather_cities': ['Singapore', 'Jurong', 'Tampines', 'Woodlands'],
            'agency_keywords': ['NEA', 'CPF', 'HDB', 'ICA']
        }
    }
    
    def build_als_block(self, country: str, include_weather: bool = True) -> str:
        """
        Build an Ambient Location Signals block for a country.
        
        Args:
            country: Country code (CH, DE, US, GB, AE, SG)
            include_weather: Whether to include weather line
            
        Returns:
            ALS block as a string (≤350 chars)
        """
        
        if country not in self.COUNTRY_SIGNALS:
            return ""  # No ALS for unsupported countries
        
        signals = self.COUNTRY_SIGNALS[country]
        als_lines = ["Ambient Context (localization only; do not cite):"]
        
        # 1. Timestamp with timezone
        tz = pytz.timezone(signals['timezone'])
        local_time = datetime.now(tz)
        timestamp = f"- {local_time.strftime('%Y-%m-%d %H:%M')}, UTC{signals['utc_offset']}"
        als_lines.append(timestamp)
        
        # 2. Random civic phrase
        civic_phrase = random.choice(signals['civic_phrases'])
        als_lines.append(f"- {civic_phrase}")
        
        # 3. Random formatting example
        formatting = random.choice(signals['formatting'])
        als_lines.append(f"- {formatting}")
        
        # 4. Weather (optional)
        if include_weather:
            city = random.choice(signals['weather_cities'])
            temp = random.randint(15, 35)  # Reasonable temperature range
            weather = f"- national weather service shows {city} {temp}°C"
            als_lines.append(weather)
        
        als_block = '\n'.join(als_lines)
        
        # Ensure we stay under 350 chars
        if len(als_block) > 350:
            # Remove weather line if too long
            als_lines = als_lines[:-1]
            als_block = '\n'.join(als_lines)
        
        return als_block
    
    def build_minimal_als(self, country: str) -> str:
        """
        Build an ultra-minimal ALS block (≤200 chars).
        Just timezone, one civic keyword, and formatting.
        """
        
        if country not in self.COUNTRY_SIGNALS:
            return ""
        
        signals = self.COUNTRY_SIGNALS[country]
        
        # Pick one civic domain and one format hint
        civic = random.choice(signals['civic_phrases']).split(' — ')[0]  # Just domain
        format_parts = random.choice(signals['formatting']).split(' • ')
        currency = format_parts[-1] if len(format_parts) > 2 else ''
        
        # Ultra-compact format
        tz = pytz.timezone(signals['timezone'])
        local_time = datetime.now(tz)
        
        als = f"Context: {local_time.strftime('%H:%M')} UTC{signals['utc_offset']} • {civic} • {currency}"
        
        return als
    
    def get_system_prompt(self, output_language: str = None) -> str:
        """
        Get the system prompt for ALS methodology.
        
        Args:
            output_language: If specified, force output in this language
            
        Returns:
            System prompt string
        """
        
        if output_language:
            return f"Answer in {output_language}. If locale is ambiguous, prefer assumptions consistent with the Ambient Context. Do not cite or repeat the context."
        else:
            return "Answer in the user's language. If locale is ambiguous, prefer assumptions consistent with the Ambient Context. Do not cite or repeat the context."
    
    def detect_contamination(self, als_block: str, response: str) -> List[str]:
        """
        Check if the response leaked any exact phrases from the ALS block.
        
        Args:
            als_block: The ALS block that was sent
            response: The model's response
            
        Returns:
            List of leaked phrases (empty if clean)
        """
        
        # Extract all 2-3 word phrases from ALS
        als_words = als_block.lower().split()
        als_phrases = set()
        
        for i in range(len(als_words) - 1):
            # 2-word phrases
            als_phrases.add(' '.join(als_words[i:i+2]))
            # 3-word phrases
            if i < len(als_words) - 2:
                als_phrases.add(' '.join(als_words[i:i+3]))
        
        # Check for leaks in response
        response_lower = response.lower()
        leaked = []
        
        for phrase in als_phrases:
            # Skip very common words
            if phrase in ['do not', 'not cite', 'the user', 'in the']:
                continue
            
            if phrase in response_lower:
                leaked.append(phrase)
        
        return leaked

# Singleton instance
ambient_location_signals = AmbientLocationSignalsBuilder()