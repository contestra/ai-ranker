'use client'

import { useState } from 'react'

export default function TestButton() {
  const [message, setMessage] = useState('')
  
  return (
    <div className="p-4 border-2 border-red-500">
      <h3 className="font-bold mb-2">Test Component</h3>
      
      {message && (
        <div className="mb-4 p-3 bg-blue-100 text-blue-800 rounded">
          {message}
        </div>
      )}
      
      <button
        onClick={() => {
          console.log('TEST BUTTON CLICKED')
          setMessage('This message should stay for 10 seconds')
          setTimeout(() => {
            console.log('Clearing message after 10 seconds')
            setMessage('')
          }, 10000)
        }}
        className="px-4 py-2 bg-red-600 text-white rounded"
      >
        Test Message Display
      </button>
      
      <button
        onClick={async () => {
          console.log('ASYNC TEST BUTTON CLICKED')
          setMessage('Step 1: Starting...')
          await new Promise(resolve => setTimeout(resolve, 2000))
          setMessage('Step 2: Processing...')
          await new Promise(resolve => setTimeout(resolve, 2000))
          setMessage('Step 3: Complete!')
          setTimeout(() => setMessage(''), 3000)
        }}
        className="ml-2 px-4 py-2 bg-green-600 text-white rounded"
      >
        Test Async Messages
      </button>
    </div>
  )
}