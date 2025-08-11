/**
 * Schema.org JSON-LD Extractor and Validator
 * Extracts and validates Product and Organization schemas using Puppeteer and Zod
 */

import puppeteer from 'puppeteer';
import { z } from 'zod';

// Schema.org AggregateRating schema
const AggregateRatingSchema = z.object({
  '@type': z.literal('AggregateRating').optional(),
  ratingValue: z.number().optional(),
  bestRating: z.number().optional(),
  worstRating: z.number().optional(),
  ratingCount: z.number().optional(),
  reviewCount: z.number().optional(),
});

// Schema.org Offer schema
const OfferSchema = z.object({
  '@type': z.literal('Offer').optional(),
  price: z.union([z.string(), z.number()]).optional(),
  priceCurrency: z.string().optional(),
  availability: z.string().optional(),
  url: z.string().url().optional(),
  seller: z.object({}).optional(),
});

// Schema.org Nutrition Information
const NutritionInformationSchema = z.object({
  '@type': z.literal('NutritionInformation').optional(),
  servingSize: z.string().optional(),
  calories: z.union([z.string(), z.number()]).optional(),
  fatContent: z.union([z.string(), z.number()]).optional(),
  proteinContent: z.union([z.string(), z.number()]).optional(),
  carbohydrateContent: z.union([z.string(), z.number()]).optional(),
});

// Schema.org Product schema (base and specialized types)
export const ProductSchema = z.object({
  '@context': z.union([z.string(), z.object({})]).optional(),
  '@type': z.enum([
    'Product',
    'SoftwareApplication',
    'WebApplication',
    'DietarySupplement',
    'Drug',
    'MedicalDevice',
    'IndividualProduct',
    'ProductModel',
    'ProductGroup',
    'Vehicle',
    'Book',
    'Movie',
    'MusicRecording',
    'Game',
    'FoodProduct',
  ]),
  '@id': z.string().optional(),
  name: z.string(),
  description: z.string().optional(),
  image: z.union([z.string(), z.array(z.string())]).optional(),
  brand: z.union([
    z.string(),
    z.object({
      '@type': z.string().optional(),
      '@id': z.string().optional(),
      name: z.string().optional(),
    }),
    z.object({ '@id': z.string() }),
  ]).optional(),
  manufacturer: z.union([
    z.string(),
    z.object({ '@id': z.string() }),
    OrganizationSchema,
  ]).optional(),
  sku: z.string().optional(),
  gtin: z.string().optional(),
  gtin8: z.string().optional(),
  gtin13: z.string().optional(),
  gtin14: z.string().optional(),
  mpn: z.string().optional(),
  offers: z.union([
    OfferSchema,
    z.array(OfferSchema),
  ]).optional(),
  aggregateRating: AggregateRatingSchema.optional(),
  review: z.array(z.object({})).optional(),
  url: z.string().url().optional(),
  
  // DietarySupplement specific fields
  isProprietary: z.boolean().optional(),
  activeIngredient: z.union([
    z.string(),
    z.array(z.string()),
  ]).optional(),
  nonActiveIngredient: z.union([
    z.string(),
    z.array(z.string()),
  ]).optional(),
  recommendedIntake: z.string().optional(),
  safetyConsideration: z.string().optional(),
  targetPopulation: z.string().optional(),
  mechanismOfAction: z.string().optional(),
  nutrition: NutritionInformationSchema.optional(),
  
  // Drug/Medical fields
  dosageForm: z.string().optional(),
  administrationRoute: z.string().optional(),
  warning: z.string().optional(),
  contraindication: z.string().optional(),
  
  // General product fields
  category: z.union([z.string(), z.array(z.string())]).optional(),
  material: z.string().optional(),
  size: z.string().optional(),
  weight: z.string().optional(),
  width: z.string().optional(),
  height: z.string().optional(),
  depth: z.string().optional(),
  additionalProperty: z.array(PropertyValueSchema).optional(),
  productID: z.string().optional(),
  productionDate: z.string().optional(),
  releaseDate: z.string().optional(),
  expirationDate: z.string().optional(),
});

// Schema.org PropertyValue for identifiers
const PropertyValueSchema = z.object({
  '@type': z.literal('PropertyValue').optional(),
  propertyID: z.string(),
  value: z.string(),
});

// Schema.org ContactPoint
const ContactPointSchema = z.object({
  '@type': z.literal('ContactPoint').optional(),
  contactType: z.string().optional(),
  email: z.string().email().optional(),
  telephone: z.string().optional(),
  url: z.string().url().optional(),
});

// Schema.org Person
const PersonSchema = z.object({
  '@type': z.literal('Person').optional(),
  '@id': z.string().optional(),
  name: z.string(),
  jobTitle: z.string().optional(),
  affiliation: z.union([z.string(), z.object({ '@id': z.string() })]).optional(),
  sameAs: z.array(z.string().url()).optional(),
});

// Schema.org Brand
const BrandSchema = z.object({
  '@type': z.literal('Brand').optional(),
  '@id': z.string().optional(),
  name: z.string(),
  alternateName: z.union([z.string(), z.array(z.string())]).optional(),
  description: z.string().optional(),
  logo: z.string().optional(),
  url: z.string().url().optional(),
  owner: z.union([z.string(), z.object({ '@id': z.string() })]).optional(),
});

// Schema.org Organization schema (enhanced)
export const OrganizationSchema = z.object({
  '@context': z.union([z.string(), z.object({})]).optional(),
  '@type': z.enum(['Organization', 'Corporation', 'LocalBusiness', 'Company']),
  '@id': z.string().optional(),
  name: z.string(),
  legalName: z.string().optional(),
  alternateName: z.union([z.string(), z.array(z.string())]).optional(),
  url: z.string().url().optional(),
  logo: z.union([
    z.string(),
    z.object({
      '@type': z.string().optional(),
      url: z.string(),
    }),
  ]).optional(),
  description: z.string().optional(),
  disambiguatingDescription: z.string().optional(),
  sameAs: z.array(z.string().url()).optional(),
  telephone: z.string().optional(),
  email: z.string().email().optional(),
  address: z.union([
    z.string(),
    z.object({
      '@type': z.literal('PostalAddress').optional(),
      streetAddress: z.string().optional(),
      addressLocality: z.string().optional(),
      addressRegion: z.string().optional(),
      postalCode: z.string().optional(),
      addressCountry: z.string().optional(),
    }),
  ]).optional(),
  founder: z.union([
    z.string(),
    z.array(z.union([
      z.string(),
      z.object({ '@id': z.string() }),
      PersonSchema,
    ])),
    z.object({ '@id': z.string() }),
    PersonSchema,
  ]).optional(),
  foundingDate: z.string().optional(),
  numberOfEmployees: z.union([z.number(), z.string()]).optional(),
  industry: z.union([z.string(), z.array(z.string())]).optional(),
  isicV4: z.string().optional(),
  naics: z.string().optional(),
  areaServed: z.union([
    z.string(),
    z.array(z.string()),
    z.object({}),
  ]).optional(),
  identifier: z.union([
    PropertyValueSchema,
    z.array(PropertyValueSchema),
  ]).optional(),
  contactPoint: z.union([
    ContactPointSchema,
    z.array(ContactPointSchema),
  ]).optional(),
  brand: z.union([
    z.string(),
    z.object({ '@id': z.string() }),
    BrandSchema,
  ]).optional(),
  parentOrganization: z.union([
    z.string(),
    z.object({ '@id': z.string() }),
  ]).optional(),
  subOrganization: z.union([
    z.array(z.union([
      z.string(),
      z.object({ '@id': z.string() }),
    ])),
    z.string(),
    z.object({ '@id': z.string() }),
  ]).optional(),
});

// Type definitions
export type ProductSchemaType = z.infer<typeof ProductSchema>;
export type OrganizationSchemaType = z.infer<typeof OrganizationSchema>;

export interface SchemaValidationResult {
  isValid: boolean;
  schemaType: string | null;
  errors: string[];
  warnings: string[];
  data: any;
  score: number; // 0-100 quality score
}

export interface WebsiteAnalysisResult {
  url: string;
  totalSchemas: number;
  products: Array<{
    type: string;
    name: string;
    validation: SchemaValidationResult;
  }>;
  organizations: Array<{
    type: string;
    name: string;
    validation: SchemaValidationResult;
  }>;
  otherSchemas: Array<{
    type: string;
    name: string;
  }>;
  overallScore: number;
}

export class SchemaExtractor {
  private browser: puppeteer.Browser | null = null;

  async init() {
    this.browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-dev-shm-usage'],
    });
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
    }
  }

  async extractSchemas(url: string): Promise<any[]> {
    if (!this.browser) {
      await this.init();
    }

    const page = await this.browser!.newPage();
    const schemas: any[] = [];

    try {
      // Navigate to page
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

      // Extract JSON-LD scripts
      const schemaScripts = await page.evaluate(() => {
        const scripts = document.querySelectorAll('script[type="application/ld+json"]');
        return Array.from(scripts).map((script) => script.textContent || '');
      });

      // Parse each schema
      for (const scriptContent of schemaScripts) {
        try {
          const schemaData = JSON.parse(scriptContent);
          
          // Handle @graph arrays
          if (schemaData['@graph']) {
            schemas.push(...schemaData['@graph']);
          } else if (Array.isArray(schemaData)) {
            schemas.push(...schemaData);
          } else {
            schemas.push(schemaData);
          }
        } catch (error) {
          console.warn('Failed to parse JSON-LD:', error);
        }
      }
    } catch (error) {
      console.error(`Error extracting schemas from ${url}:`, error);
    } finally {
      await page.close();
    }

    return schemas;
  }

  validateProductSchema(schemaData: any): SchemaValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    let score = 100;

    try {
      // Check if it's a product type
      const schemaType = schemaData['@type'];
      const productTypes = [
        'Product', 'SoftwareApplication', 'WebApplication', 'DietarySupplement',
        'Drug', 'MedicalDevice', 'IndividualProduct', 'ProductModel', 'ProductGroup',
        'Vehicle', 'Book', 'Movie', 'MusicRecording', 'Game', 'FoodProduct'
      ];
      
      if (!productTypes.includes(schemaType)) {
        return {
          isValid: false,
          schemaType: null,
          errors: [`Not a Product schema: ${schemaType}`],
          warnings: [],
          data: null,
          score: 0,
        };
      }

      // Validate with Zod
      const result = ProductSchema.safeParse(schemaData);
      
      if (!result.success) {
        errors.push(...result.error.errors.map(e => `${e.path.join('.')}: ${e.message}`));
        return {
          isValid: false,
          schemaType,
          errors,
          warnings,
          data: schemaData,
          score: 0,
        };
      }

      const product = result.data;

      // Calculate quality score and warnings
      if (!product.description) {
        warnings.push('Missing description');
        score -= 10;
      }
      if (!product.image) {
        warnings.push('Missing product images');
        score -= 15;
      }
      if (!product.brand) {
        warnings.push('Missing brand information');
        score -= 10;
      }
      if (!product.offers) {
        warnings.push('Missing offer/pricing information');
        score -= 15;
      }
      if (!product.aggregateRating && !product.review) {
        warnings.push('Missing ratings or reviews');
        score -= 8;
      }
      if (!product.sku && !product.gtin && !product.mpn && !product.productID) {
        warnings.push('Missing product identifiers (SKU/GTIN/MPN)');
        score -= 5;
      }
      
      // Type-specific validation
      if (schemaType === 'DietarySupplement' || schemaType === 'Drug') {
        if (!product.activeIngredient) {
          warnings.push('Missing active ingredients');
          score -= 10;
        }
        if (!product.recommendedIntake && !product.dosageForm) {
          warnings.push('Missing dosage/intake information');
          score -= 5;
        }
        if (!product.warning && !product.safetyConsideration) {
          warnings.push('Missing safety/warning information');
          score -= 5;
        }
      }
      
      // Bonus points for enhanced data
      if (product['@id']) {
        score += 3; // Has @id for linking
      }
      if (product.manufacturer) {
        score += 2; // Has manufacturer info
      }
      if (product.category) {
        score += 2; // Has categorization
      }
      
      // Ensure score stays within bounds
      score = Math.min(Math.max(score, 0), 100);

      return {
        isValid: true,
        schemaType,
        errors,
        warnings,
        data: product,
        score: Math.max(score, 0),
      };
    } catch (error) {
      errors.push(String(error));
      return {
        isValid: false,
        schemaType: schemaData['@type'],
        errors,
        warnings,
        data: schemaData,
        score: 0,
      };
    }
  }

  validateOrganizationSchema(schemaData: any): SchemaValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    let score = 100;

    try {
      // Check if it's an organization type
      const schemaType = schemaData['@type'];
      if (!['Organization', 'Corporation', 'LocalBusiness', 'Company'].includes(schemaType)) {
        return {
          isValid: false,
          schemaType: null,
          errors: [`Not an Organization schema: ${schemaType}`],
          warnings: [],
          data: null,
          score: 0,
        };
      }

      // Validate with Zod
      const result = OrganizationSchema.safeParse(schemaData);
      
      if (!result.success) {
        errors.push(...result.error.errors.map(e => `${e.path.join('.')}: ${e.message}`));
        return {
          isValid: false,
          schemaType,
          errors,
          warnings,
          data: schemaData,
          score: 0,
        };
      }

      const org = result.data;

      // Advanced scoring for quality
      // Essential fields
      if (!org.url) {
        warnings.push('Missing website URL');
        score -= 10;
      }
      if (!org.logo) {
        warnings.push('Missing logo');
        score -= 10;
      }
      if (!org.description && !org.disambiguatingDescription) {
        warnings.push('Missing description');
        score -= 10;
      }
      
      // Important fields
      if (!org.sameAs || org.sameAs.length === 0) {
        warnings.push('Missing social media links (sameAs)');
        score -= 8;
      }
      if (!org.address) {
        warnings.push('Missing address information');
        score -= 5;
      }
      if (!org.telephone && !org.email && !org.contactPoint) {
        warnings.push('Missing contact information');
        score -= 8;
      }
      
      // Good-to-have fields
      if (!org.legalName) {
        warnings.push('Missing legal name');
        score -= 3;
      }
      if (!org.foundingDate) {
        warnings.push('Missing founding date');
        score -= 3;
      }
      if (!org.founder) {
        warnings.push('Missing founder information');
        score -= 3;
      }
      
      // Advanced structured data
      if (!org.identifier) {
        warnings.push('Missing business identifiers (tax ID, registration numbers)');
        score -= 5;
      }
      if (!org.industry && !org.isicV4 && !org.naics) {
        warnings.push('Missing industry classification');
        score -= 3;
      }
      if (!org.areaServed) {
        warnings.push('Missing area served information');
        score -= 3;
      }
      
      // Bonus points for exceptional structured data
      if (org['@id']) {
        score += 5; // Has @id for linking
      }
      if (org.disambiguatingDescription) {
        score += 5; // Has disambiguation (important for AVEA!)
      }
      if (org.brand) {
        score += 3; // Has brand information
      }
      if (org.subOrganization || org.parentOrganization) {
        score += 3; // Has organizational structure
      }
      if (org.alternateName) {
        score += 2; // Has alternate names
      }

      // Ensure score stays within bounds
      score = Math.min(Math.max(score, 0), 100);

      return {
        isValid: true,
        schemaType,
        errors,
        warnings,
        data: org,
        score,
      };
    } catch (error) {
      errors.push(String(error));
      return {
        isValid: false,
        schemaType: schemaData['@type'],
        errors,
        warnings,
        data: schemaData,
        score: 0,
      };
    }
  }

  async analyzeWebsite(url: string): Promise<WebsiteAnalysisResult> {
    const schemas = await this.extractSchemas(url);
    
    const results: WebsiteAnalysisResult = {
      url,
      totalSchemas: schemas.length,
      products: [],
      organizations: [],
      otherSchemas: [],
      overallScore: 0,
    };

    const productTypes = [
      'Product', 'SoftwareApplication', 'WebApplication', 'DietarySupplement',
      'Drug', 'MedicalDevice', 'IndividualProduct', 'ProductModel', 'ProductGroup',
      'Vehicle', 'Book', 'Movie', 'MusicRecording', 'Game', 'FoodProduct'
    ];
    
    const orgTypes = ['Organization', 'Corporation', 'LocalBusiness', 'Company'];

    for (const schema of schemas) {
      const schemaType = schema['@type'];

      // Check for Product schemas (including specialized types)
      if (productTypes.includes(schemaType)) {
        const validation = this.validateProductSchema(schema);
        results.products.push({
          type: schemaType,
          name: schema.name || 'Unknown',
          validation,
        });
      }
      // Check for Organization schemas
      else if (orgTypes.includes(schemaType)) {
        const validation = this.validateOrganizationSchema(schema);
        results.organizations.push({
          type: schemaType,
          name: schema.name || 'Unknown',
          validation,
        });
      }
      // Other schemas (Brand, Person, etc.)
      else {
        results.otherSchemas.push({
          type: schemaType,
          name: schema.name || 'Unknown',
        });
      }
    }

    // Calculate overall score
    const allScores: number[] = [];
    results.products.forEach(p => allScores.push(p.validation.score));
    results.organizations.forEach(o => allScores.push(o.validation.score));

    if (allScores.length > 0) {
      results.overallScore = Math.floor(
        allScores.reduce((a, b) => a + b, 0) / allScores.length
      );
    }

    return results;
  }
}

// Example usage
export async function analyzeWebsiteSchemas(url: string) {
  const extractor = new SchemaExtractor();
  
  try {
    await extractor.init();
    const results = await extractor.analyzeWebsite(url);
    
    console.log(`\nAnalysis for ${url}`);
    console.log(`Total schemas found: ${results.totalSchemas}`);
    console.log(`Overall score: ${results.overallScore}/100`);
    
    if (results.organizations.length > 0) {
      console.log('\nOrganization Schemas:');
      results.organizations.forEach(org => {
        const { validation } = org;
        console.log(`  - ${org.name} (${org.type})`);
        console.log(`    Valid: ${validation.isValid}, Score: ${validation.score}/100`);
        if (validation.warnings.length > 0) {
          console.log(`    Warnings: ${validation.warnings.join(', ')}`);
        }
      });
    }
    
    if (results.products.length > 0) {
      console.log('\nProduct Schemas:');
      results.products.forEach(product => {
        const { validation } = product;
        console.log(`  - ${product.name} (${product.type})`);
        console.log(`    Valid: ${validation.isValid}, Score: ${validation.score}/100`);
        if (validation.warnings.length > 0) {
          console.log(`    Warnings: ${validation.warnings.join(', ')}`);
        }
      });
    }
    
    return results;
  } finally {
    await extractor.close();
  }
}