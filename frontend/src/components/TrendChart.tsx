import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendData } from '@/types'

interface TrendChartProps {
  data: TrendData[]
}

export default function TrendChart({ data }: TrendChartProps) {
  const formattedData = data.map(d => ({
    ...d,
    mention_rate: d.mention_rate * 100,
    weighted_score: d.weighted_score * 100,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={formattedData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line 
          type="monotone" 
          dataKey="mention_rate" 
          stroke="#8884d8" 
          name="Mention Rate (%)"
        />
        <Line 
          type="monotone" 
          dataKey="weighted_score" 
          stroke="#82ca9d" 
          name="Weighted Score (%)"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}