import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/20/solid'

interface ScoreCardProps {
  title: string
  value?: number | null
  format?: 'percentage' | 'rank' | 'number'
  trend?: 'up' | 'down' | 'stable'
  confidence?: [number, number]
}

export default function ScoreCard({ title, value, format = 'number', trend, confidence }: ScoreCardProps) {
  const formatValue = () => {
    if (value === null || value === undefined) {
      return 'N/A'
    }
    
    switch (format) {
      case 'percentage':
        return `${(value * 100).toFixed(1)}%`
      case 'rank':
        return value === Infinity ? 'Not ranked' : `#${value.toFixed(1)}`
      default:
        return value.toFixed(2)
    }
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-500">{title}</h3>
        {trend && (
          <span className={`inline-flex items-center text-sm ${
            trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-500'
          }`}>
            {trend === 'up' && <ArrowUpIcon className="h-4 w-4 mr-1" />}
            {trend === 'down' && <ArrowDownIcon className="h-4 w-4 mr-1" />}
            {trend === 'stable' && <span className="mr-1">-</span>}
            {trend}
          </span>
        )}
      </div>
      <div className="mt-2">
        <p className="text-3xl font-semibold text-gray-900">{formatValue()}</p>
        {confidence && (
          <p className="text-sm text-gray-500 mt-1">
            CI: [{(confidence[0] * 100).toFixed(1)}%, {(confidence[1] * 100).toFixed(1)}%]
          </p>
        )}
      </div>
    </div>
  )
}