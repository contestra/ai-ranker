export const GROUNDING_MODES = {
  NOT_GROUNDED: 'not_grounded',
  PREFERRED: 'preferred',
  ENFORCED: 'enforced'
} as const;

export type GroundingMode = typeof GROUNDING_MODES[keyof typeof GROUNDING_MODES];

// Provider detection helper
export function getProviderFromModel(modelName: string | null | undefined): 'openai' | 'vertex' | 'unknown' {
  if (!modelName) return 'unknown';
  const model = modelName.toLowerCase();
  if (model.includes('gpt')) return 'openai';
  if (model.includes('gemini') || model.includes('publishers/google')) return 'vertex';
  return 'unknown';
}

export function getGroundingDisplayLabel(
  mode: GroundingMode | string | null | undefined,
  modelNameOrProvider: string | null | undefined
): string {
  if (!mode) return 'Unknown';
  if (!modelNameOrProvider) return String(mode);
  
  const provider = modelNameOrProvider.length <= 10 
    ? modelNameOrProvider 
    : getProviderFromModel(modelNameOrProvider);
    
  if (provider === 'openai') {
    switch (mode) {
      case GROUNDING_MODES.NOT_GROUNDED:
      case 'none':
      case 'off':
        return 'No Grounding';
      case GROUNDING_MODES.PREFERRED:
      case 'web':
      case 'preferred':
        return 'Web Search (Auto)';
      case GROUNDING_MODES.ENFORCED:
      case 'required':
      case 'enforced':
        return 'Web Search (Required)';
      default:
        return mode;
    }
  }
  if (provider === 'vertex') {
    switch (mode) {
      case GROUNDING_MODES.NOT_GROUNDED:
      case 'none':
      case 'off':
        return 'No Grounding';
      case GROUNDING_MODES.PREFERRED:
      case 'web':
      case 'preferred':
        return 'Web Search (Auto — model decides)';
      case GROUNDING_MODES.ENFORCED:
      case 'required':
      case 'enforced':
        return 'Web Search (App-enforced)';
      default:
        return mode;
    }
  }
  return mode;
}

// Legacy mode mapping for backward compatibility
export function mapLegacyMode(mode: string | null | undefined): GroundingMode {
  if (!mode) return GROUNDING_MODES.NOT_GROUNDED;
  
  const modeMap: Record<string, GroundingMode> = {
    'off': GROUNDING_MODES.NOT_GROUNDED,
    'none': GROUNDING_MODES.NOT_GROUNDED,
    'ungrounded': GROUNDING_MODES.NOT_GROUNDED,
    'model knowledge only': GROUNDING_MODES.NOT_GROUNDED,
    'web': GROUNDING_MODES.PREFERRED,
    'grounded': GROUNDING_MODES.PREFERRED,
    'grounded (web search)': GROUNDING_MODES.PREFERRED,
    'auto': GROUNDING_MODES.PREFERRED,
    'preferred': GROUNDING_MODES.PREFERRED,
    'required': GROUNDING_MODES.ENFORCED,
    'enforced': GROUNDING_MODES.ENFORCED
  };
  
  const normalized = mode.toLowerCase().trim();
  return modeMap[normalized] || GROUNDING_MODES.NOT_GROUNDED;
}