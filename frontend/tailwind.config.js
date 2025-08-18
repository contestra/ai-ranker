/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ['class'],
    content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
  	extend: {
  		colors: {
  			contestra: {
  				dark: '#1A1E22',
  				text: '#212529',
  				'text-meta': '#474350',
  				accent: '#ff0088',
  				green: '#2D8A2D',
  				blue: '#3D70B8',
  				orange: '#D96D14',
  				'highlight-yellow': '#FFFF80',
  				'highlight-purple': '#6633CC',
  				'gray-50': '#FEFEFE',
  				'gray-75': '#FCFCFC',
  				'gray-100': '#F8F9FA',
  				'gray-300': '#DEE2E6',
  				'gray-500': '#ADB5BD',
  				'gray-700': '#495057',
  				'gray-900': '#212529',
  				'gray-950': '#1A1E22',
  				'gray-1000': '#111315',
  				black: '#000000',
  				'sparkle-cyan': '#35FDF3',
  				'sparkle-yellow': '#FEFFCC',
  				'sparkle-pink': '#FFE6F3',
  				'sparkle-blue': '#4567FF'
  			}
  		},
  		fontFamily: {
  			display: [
  				'Suisse Screen',
  				'system-ui',
  				'sans-serif'
  			],
  			body: [
  				'Suisse Intl',
  				'system-ui',
  				'sans-serif'
  			],
  			mono: [
  				'Suisse Intl Mono',
  				'monospace'
  			]
  		},
  		backgroundImage: {
  			spectrum: 'linear-gradient(to right, #f2ffff 0%, #f2fff9 20%, #f9fff2 35%, #fffff2 50%, #fff9f2 65%, #fff2f9 80%, #fff2f5 100%)',
  			'spectrum-70': 'linear-gradient(to right, #b3ffff 0%, #b3ffdb 20%, #dbffb3 35%, #ffffb3 50%, #ffdbb3 65%, #ffb3db 80%, #ffb3c7 100%)',
  			'spectrum-90': 'linear-gradient(to right, #E6FFFF 0%, #E6FFF3 20%, #F3FFE6 35%, #FFFFE6 50%, #FFF3E6 65%, #FFE6F3 80%, #FFE6EC 100%)',
  			'spectrum-subtle': 'linear-gradient(to right, #f9ffff 0%, #f9fffc 20%, #fcfff9 35%, #fffff9 50%, #fffcf9 65%, #fff9fc 80%, #fff9fa 100%)'
  		},
  		boxShadow: {
  			'contestra-sm': '0 1px 2px rgba(0, 0, 0, 0.05)',
  			'contestra-md': '0 4px 15px rgba(0, 0, 0, 0.1)',
  			'contestra-lg': '0 6px 20px rgba(0, 0, 0, 0.15)',
  			'contestra-xl': '0 10px 30px rgba(0, 0, 0, 0.1)'
  		},
  		animation: {
  			gradient: 'gradient 3s ease infinite',
  			sparkle: 'sparkle 2s ease infinite',
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		},
  		keyframes: {
  			gradient: {
  				'0%, 100%': {
  					backgroundPosition: '0% 50%'
  				},
  				'50%': {
  					backgroundPosition: '100% 50%'
  				}
  			},
  			sparkle: {
  				'0%, 100%': {
  					opacity: 0
  				},
  				'50%': {
  					opacity: 1
  				}
  			},
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		}
  	}
  },
  plugins: [],
}