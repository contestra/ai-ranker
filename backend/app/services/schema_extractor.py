"""
Schema.org JSON-LD Extractor and Validator
Extracts and validates Product and Organization schemas from websites
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from pyppeteer import launch
from pydantic import BaseModel, Field, HttpUrl, validator
import logging

logger = logging.getLogger(__name__)


class SchemaType(str, Enum):
    ORGANIZATION = "Organization"
    CORPORATION = "Corporation"
    LOCAL_BUSINESS = "LocalBusiness"
    PRODUCT = "Product"
    SOFTWARE_APPLICATION = "SoftwareApplication"
    WEB_APPLICATION = "WebApplication"


class AggregateRating(BaseModel):
    """Schema.org AggregateRating"""
    type: str = Field(alias="@type", default="AggregateRating")
    rating_value: Optional[float] = Field(alias="ratingValue", default=None)
    best_rating: Optional[float] = Field(alias="bestRating", default=None)
    worst_rating: Optional[float] = Field(alias="worstRating", default=None)
    rating_count: Optional[int] = Field(alias="ratingCount", default=None)
    review_count: Optional[int] = Field(alias="reviewCount", default=None)

    class Config:
        populate_by_name = True


class Offer(BaseModel):
    """Schema.org Offer"""
    type: str = Field(alias="@type", default="Offer")
    price: Optional[str] = Field(default=None)
    price_currency: Optional[str] = Field(alias="priceCurrency", default=None)
    availability: Optional[str] = Field(default=None)
    url: Optional[HttpUrl] = Field(default=None)
    seller: Optional[Dict] = Field(default=None)

    class Config:
        populate_by_name = True


class ProductSchema(BaseModel):
    """Schema.org Product validation model"""
    context: Optional[str] = Field(alias="@context", default="https://schema.org")
    type: str = Field(alias="@type")
    name: str
    description: Optional[str] = Field(default=None)
    image: Optional[List[str]] = Field(default=None)
    brand: Optional[Dict[str, str]] = Field(default=None)
    sku: Optional[str] = Field(default=None)
    gtin: Optional[str] = Field(default=None)
    gtin8: Optional[str] = Field(default=None)
    gtin13: Optional[str] = Field(default=None)
    gtin14: Optional[str] = Field(default=None)
    mpn: Optional[str] = Field(default=None)
    offers: Optional[List[Dict]] = Field(default=None)
    aggregate_rating: Optional[Dict] = Field(alias="aggregateRating", default=None)
    review: Optional[List[Dict]] = Field(default=None)
    url: Optional[HttpUrl] = Field(default=None)

    @validator('type')
    def validate_type(cls, v):
        if v not in ["Product", "SoftwareApplication", "WebApplication"]:
            raise ValueError(f"Invalid product type: {v}")
        return v

    class Config:
        populate_by_name = True


class OrganizationSchema(BaseModel):
    """Schema.org Organization validation model"""
    context: Optional[str] = Field(alias="@context", default="https://schema.org")
    type: str = Field(alias="@type")
    name: str
    url: Optional[HttpUrl] = Field(default=None)
    logo: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    same_as: Optional[List[HttpUrl]] = Field(alias="sameAs", default=None)
    telephone: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    address: Optional[Dict] = Field(default=None)
    founder: Optional[Dict] = Field(default=None)
    founding_date: Optional[str] = Field(alias="foundingDate", default=None)
    employees: Optional[int] = Field(alias="numberOfEmployees", default=None)
    
    @validator('type')
    def validate_type(cls, v):
        if v not in ["Organization", "Corporation", "LocalBusiness", "Company"]:
            raise ValueError(f"Invalid organization type: {v}")
        return v

    class Config:
        populate_by_name = True


@dataclass
class SchemaValidationResult:
    """Result of schema validation"""
    is_valid: bool
    schema_type: Optional[str]
    errors: List[str]
    warnings: List[str]
    data: Optional[Dict[str, Any]]
    score: int  # 0-100 quality score


class SchemaExtractor:
    """Extracts and validates JSON-LD schemas from websites"""
    
    def __init__(self):
        self.browser = None
        
    async def __aenter__(self):
        self.browser = await launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
    
    async def extract_schemas(self, url: str) -> List[Dict[str, Any]]:
        """Extract all JSON-LD schemas from a webpage"""
        if not self.browser:
            self.browser = await launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
        page = await self.browser.newPage()
        schemas = []
        
        try:
            # Navigate to page
            await page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 30000})
            
            # Extract JSON-LD scripts
            schema_scripts = await page.evaluate('''() => {
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                return Array.from(scripts).map(script => script.textContent);
            }''')
            
            # Parse each schema
            for script_content in schema_scripts:
                try:
                    schema_data = json.loads(script_content)
                    # Handle @graph arrays
                    if isinstance(schema_data, dict) and '@graph' in schema_data:
                        schemas.extend(schema_data['@graph'])
                    elif isinstance(schema_data, list):
                        schemas.extend(schema_data)
                    else:
                        schemas.append(schema_data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON-LD: {e}")
                    
        except Exception as e:
            logger.error(f"Error extracting schemas from {url}: {e}")
        finally:
            await page.close()
            
        return schemas
    
    def validate_product_schema(self, schema_data: Dict) -> SchemaValidationResult:
        """Validate a Product schema"""
        errors = []
        warnings = []
        score = 100
        
        try:
            # Check if it's a product type
            schema_type = schema_data.get('@type', '')
            if schema_type not in ['Product', 'SoftwareApplication', 'WebApplication']:
                return SchemaValidationResult(
                    is_valid=False,
                    schema_type=None,
                    errors=[f"Not a Product schema: {schema_type}"],
                    warnings=[],
                    data=None,
                    score=0
                )
            
            # Validate with Pydantic
            product = ProductSchema(**schema_data)
            
            # Calculate quality score
            if not product.description:
                warnings.append("Missing description")
                score -= 10
            if not product.image:
                warnings.append("Missing product images")
                score -= 15
            if not product.brand:
                warnings.append("Missing brand information")
                score -= 10
            if not product.offers:
                warnings.append("Missing offer/pricing information")
                score -= 20
            if not product.aggregate_rating and not product.review:
                warnings.append("Missing ratings or reviews")
                score -= 10
            if not product.sku and not product.gtin and not product.mpn:
                warnings.append("Missing product identifiers (SKU/GTIN/MPN)")
                score -= 5
                
            return SchemaValidationResult(
                is_valid=True,
                schema_type=schema_type,
                errors=errors,
                warnings=warnings,
                data=product.dict(by_alias=True, exclude_none=True),
                score=max(score, 0)
            )
            
        except Exception as e:
            errors.append(str(e))
            return SchemaValidationResult(
                is_valid=False,
                schema_type=schema_data.get('@type'),
                errors=errors,
                warnings=warnings,
                data=schema_data,
                score=0
            )
    
    def validate_organization_schema(self, schema_data: Dict) -> SchemaValidationResult:
        """Validate an Organization schema"""
        errors = []
        warnings = []
        score = 100
        
        try:
            # Check if it's an organization type
            schema_type = schema_data.get('@type', '')
            if schema_type not in ['Organization', 'Corporation', 'LocalBusiness', 'Company']:
                return SchemaValidationResult(
                    is_valid=False,
                    schema_type=None,
                    errors=[f"Not an Organization schema: {schema_type}"],
                    warnings=[],
                    data=None,
                    score=0
                )
            
            # Validate with Pydantic
            org = OrganizationSchema(**schema_data)
            
            # Calculate quality score
            if not org.url:
                warnings.append("Missing website URL")
                score -= 10
            if not org.logo:
                warnings.append("Missing logo")
                score -= 10
            if not org.description:
                warnings.append("Missing description")
                score -= 15
            if not org.same_as:
                warnings.append("Missing social media links (sameAs)")
                score -= 10
            if not org.address:
                warnings.append("Missing address information")
                score -= 5
            if not org.telephone and not org.email:
                warnings.append("Missing contact information")
                score -= 10
                
            return SchemaValidationResult(
                is_valid=True,
                schema_type=schema_type,
                errors=errors,
                warnings=warnings,
                data=org.dict(by_alias=True, exclude_none=True),
                score=max(score, 0)
            )
            
        except Exception as e:
            errors.append(str(e))
            return SchemaValidationResult(
                is_valid=False,
                schema_type=schema_data.get('@type'),
                errors=errors,
                warnings=warnings,
                data=schema_data,
                score=0
            )
    
    async def analyze_website(self, url: str) -> Dict[str, Any]:
        """Analyze a website's Product and Organization schemas"""
        schemas = await self.extract_schemas(url)
        
        results = {
            'url': url,
            'total_schemas': len(schemas),
            'products': [],
            'organizations': [],
            'other_schemas': [],
            'overall_score': 0
        }
        
        for schema in schemas:
            schema_type = schema.get('@type', '')
            
            # Check for Product schemas
            if schema_type in ['Product', 'SoftwareApplication', 'WebApplication']:
                validation = self.validate_product_schema(schema)
                results['products'].append({
                    'type': schema_type,
                    'name': schema.get('name', 'Unknown'),
                    'validation': validation
                })
            
            # Check for Organization schemas
            elif schema_type in ['Organization', 'Corporation', 'LocalBusiness', 'Company']:
                validation = self.validate_organization_schema(schema)
                results['organizations'].append({
                    'type': schema_type,
                    'name': schema.get('name', 'Unknown'),
                    'validation': validation
                })
            
            else:
                results['other_schemas'].append({
                    'type': schema_type,
                    'name': schema.get('name', 'Unknown')
                })
        
        # Calculate overall score
        all_scores = []
        for product in results['products']:
            all_scores.append(product['validation'].score)
        for org in results['organizations']:
            all_scores.append(org['validation'].score)
            
        if all_scores:
            results['overall_score'] = sum(all_scores) // len(all_scores)
        
        return results


# Example usage
async def main():
    url = "https://www.example.com"
    
    async with SchemaExtractor() as extractor:
        results = await extractor.analyze_website(url)
        
        print(f"\nAnalysis for {url}")
        print(f"Total schemas found: {results['total_schemas']}")
        print(f"Overall score: {results['overall_score']}/100")
        
        if results['organizations']:
            print("\nOrganization Schemas:")
            for org in results['organizations']:
                validation = org['validation']
                print(f"  - {org['name']} ({org['type']})")
                print(f"    Valid: {validation.is_valid}, Score: {validation.score}/100")
                if validation.warnings:
                    print(f"    Warnings: {', '.join(validation.warnings)}")
        
        if results['products']:
            print("\nProduct Schemas:")
            for product in results['products']:
                validation = product['validation']
                print(f"  - {product['name']} ({product['type']})")
                print(f"    Valid: {validation.is_valid}, Score: {validation.score}/100")
                if validation.warnings:
                    print(f"    Warnings: {', '.join(validation.warnings)}")


if __name__ == "__main__":
    asyncio.run(main())