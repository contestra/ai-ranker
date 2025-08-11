/**
 * Test script for Schema.org extraction and validation
 * Tests Product and Organization schemas including DietarySupplement
 */

const { SchemaExtractor } = require('../frontend/src/lib/schemaExtractor');

async function testSchemaExtraction() {
  const extractor = new SchemaExtractor();
  
  try {
    await extractor.init();
    console.log('Schema Extractor initialized\n');
    
    // Test websites
    const testUrls = [
      'https://www.avea-life.com',  // Has complex Organization and DietarySupplement schemas
      // Add more test URLs here as needed
    ];
    
    for (const url of testUrls) {
      console.log('═'.repeat(60));
      console.log(`Analyzing: ${url}`);
      console.log('═'.repeat(60));
      
      try {
        const results = await extractor.analyzeWebsite(url);
        
        // Summary
        console.log(`\n📊 SUMMARY`);
        console.log(`Total schemas found: ${results.totalSchemas}`);
        console.log(`Overall score: ${results.overallScore}/100`);
        console.log(`Organizations: ${results.organizations.length}`);
        console.log(`Products: ${results.products.length}`);
        console.log(`Other schemas: ${results.otherSchemas.length}`);
        
        // Organization Details
        if (results.organizations.length > 0) {
          console.log('\n🏢 ORGANIZATION SCHEMAS:');
          results.organizations.forEach((org, index) => {
            const { validation } = org;
            console.log(`\n  ${index + 1}. ${org.name} (${org.type})`);
            console.log(`     Valid: ${validation.isValid ? '✅' : '❌'}`);
            console.log(`     Score: ${validation.score}/100`);
            
            // Show key fields if valid
            if (validation.isValid && validation.data) {
              const data = validation.data;
              if (data.legalName) console.log(`     Legal Name: ${data.legalName}`);
              if (data.foundingDate) console.log(`     Founded: ${data.foundingDate}`);
              if (data.disambiguatingDescription) {
                console.log(`     Disambiguation: ${data.disambiguatingDescription.substring(0, 80)}...`);
              }
              if (data.identifier && Array.isArray(data.identifier)) {
                console.log(`     Identifiers: ${data.identifier.length} business IDs`);
              }
              if (data['@id']) console.log(`     Has @id: ✅ (linked data)`);
            }
            
            // Show warnings
            if (validation.warnings.length > 0) {
              console.log(`     ⚠️  Warnings:`);
              validation.warnings.forEach(w => console.log(`        - ${w}`));
            }
            
            // Show errors
            if (validation.errors.length > 0) {
              console.log(`     ❌ Errors:`);
              validation.errors.forEach(e => console.log(`        - ${e}`));
            }
          });
        }
        
        // Product Details
        if (results.products.length > 0) {
          console.log('\n📦 PRODUCT SCHEMAS:');
          results.products.forEach((product, index) => {
            const { validation } = product;
            console.log(`\n  ${index + 1}. ${product.name} (${product.type})`);
            console.log(`     Valid: ${validation.isValid ? '✅' : '❌'}`);
            console.log(`     Score: ${validation.score}/100`);
            
            // Show key fields for DietarySupplement
            if (validation.isValid && validation.data) {
              const data = validation.data;
              if (product.type === 'DietarySupplement') {
                console.log(`     Type: DietarySupplement 💊`);
                if (data.activeIngredient) {
                  const ingredients = Array.isArray(data.activeIngredient) 
                    ? data.activeIngredient.length 
                    : 1;
                  console.log(`     Active Ingredients: ${ingredients} listed`);
                }
                if (data.isProprietary) console.log(`     Proprietary: ✅`);
                if (data.recommendedIntake) console.log(`     Dosage: ${data.recommendedIntake}`);
              }
              if (data['@id']) console.log(`     Has @id: ✅ (linked data)`);
              if (data.manufacturer) console.log(`     Has manufacturer: ✅`);
            }
            
            // Show warnings
            if (validation.warnings.length > 0) {
              console.log(`     ⚠️  Warnings:`);
              validation.warnings.forEach(w => console.log(`        - ${w}`));
            }
            
            // Show errors
            if (validation.errors.length > 0) {
              console.log(`     ❌ Errors:`);
              validation.errors.forEach(e => console.log(`        - ${e}`));
            }
          });
        }
        
        // Other Schemas
        if (results.otherSchemas.length > 0) {
          console.log('\n📋 OTHER SCHEMAS:');
          results.otherSchemas.forEach(schema => {
            console.log(`  - ${schema.name || 'Unnamed'} (${schema.type})`);
          });
        }
        
        // Recommendations
        console.log('\n💡 RECOMMENDATIONS:');
        if (results.overallScore < 50) {
          console.log('  ⚠️  Schema quality needs significant improvement');
        } else if (results.overallScore < 75) {
          console.log('  ℹ️  Schema quality is good but could be enhanced');
        } else {
          console.log('  ✅ Excellent schema implementation!');
        }
        
        // Check for disambiguation (important for AVEA)
        const hasDisambiguation = results.organizations.some(
          org => org.validation.data?.disambiguatingDescription
        );
        if (!hasDisambiguation && results.organizations.length > 0) {
          console.log('  💡 Consider adding disambiguatingDescription to differentiate from similar brands');
        }
        
      } catch (error) {
        console.error(`\n❌ Error analyzing ${url}:`, error.message);
      }
      
      console.log('\n');
    }
    
  } catch (error) {
    console.error('Fatal error:', error);
  } finally {
    await extractor.close();
    console.log('Schema Extractor closed');
  }
}

// Run the test
console.log('🔍 Schema.org Extraction & Validation Tool\n');
testSchemaExtraction().catch(console.error);