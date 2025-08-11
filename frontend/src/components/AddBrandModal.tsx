'use client'

import { useState, Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { brandsApi } from '@/lib/api'

interface AddBrandModalProps {
  isOpen: boolean
  onClose: () => void
  onBrandAdded: () => void
}

export default function AddBrandModal({ isOpen, onClose, onBrandAdded }: AddBrandModalProps) {
  const [brandName, setBrandName] = useState('')
  const [domain, setDomain] = useState('')
  const [categories, setCategories] = useState('')
  const [aliases, setAliases] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!brandName.trim()) {
      setError('Brand name is required')
      return
    }

    setLoading(true)
    setError('')

    try {
      const categoryArray = categories.split(',').map(c => c.trim()).filter(c => c)
      const aliasArray = aliases.split(',').map(a => a.trim()).filter(a => a)

      await brandsApi.create({
        name: brandName,
        domain: domain || undefined,
        category: categoryArray,
        aliases: aliasArray,
        wikidata_qid: undefined
      })

      // Reset form
      setBrandName('')
      setDomain('')
      setCategories('')
      setAliases('')
      
      onBrandAdded()
      onClose()
    } catch (err) {
      setError('Failed to create brand. Please try again.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-10" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <Dialog.Title
                  as="h3"
                  className="text-lg font-medium leading-6 text-gray-900"
                >
                  Add New Brand
                </Dialog.Title>
                
                <form onSubmit={handleSubmit} className="mt-4">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Brand Name *
                      </label>
                      <input
                        type="text"
                        value={brandName}
                        onChange={(e) => setBrandName(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                        placeholder="e.g., Tesla"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Domain
                      </label>
                      <input
                        type="text"
                        value={domain}
                        onChange={(e) => setDomain(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                        placeholder="e.g., tesla.com"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Categories (comma-separated)
                      </label>
                      <input
                        type="text"
                        value={categories}
                        onChange={(e) => setCategories(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                        placeholder="e.g., automotive, electric vehicles, technology"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Aliases (comma-separated)
                      </label>
                      <input
                        type="text"
                        value={aliases}
                        onChange={(e) => setAliases(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
                        placeholder="e.g., TSLA, Tesla Inc, Tesla Motors"
                      />
                    </div>
                  </div>

                  {error && (
                    <p className="mt-2 text-sm text-red-600">{error}</p>
                  )}

                  <div className="mt-6 flex justify-end space-x-3">
                    <button
                      type="button"
                      className="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                      onClick={onClose}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={loading}
                      className="inline-flex justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? 'Creating...' : 'Create Brand'}
                    </button>
                  </div>
                </form>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}