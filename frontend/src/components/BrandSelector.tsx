'use client'

import { useState, useEffect, Fragment } from 'react'
import { Listbox, Transition } from '@headlessui/react'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/react/20/solid'
import { Brand } from '@/types'
import { brandsApi } from '@/lib/api'

interface BrandSelectorProps {
  onSelect: (brand: Brand | null) => void
}

export default function BrandSelector({ onSelect }: BrandSelectorProps) {
  const [brands, setBrands] = useState<Brand[]>([])
  const [selected, setSelected] = useState<Brand | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadBrands()
  }, [])

  const loadBrands = async () => {
    try {
      console.log('Loading brands...')
      const data = await brandsApi.list()
      console.log('Brands loaded:', data)
      setBrands(data)
      if (data.length > 0) {
        setSelected(data[0])
        onSelect(data[0])
      }
    } catch (error) {
      console.error('Failed to load brands:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (brand: Brand) => {
    setSelected(brand)
    onSelect(brand)
  }

  if (loading) {
    return <div className="w-64 h-10 bg-gray-200 animate-pulse rounded-md"></div>
  }

  if (brands.length === 0) {
    return (
      <div className="text-sm text-gray-500">
        No brands configured. Please add brands via API.
      </div>
    )
  }

  return (
    <Listbox value={selected} onChange={handleSelect}>
      <div className="relative w-64">
        <Listbox.Button className="relative w-full cursor-default rounded-lg bg-white py-2 pl-3 pr-10 text-left shadow-md focus:outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75 focus-visible:ring-offset-2 focus-visible:ring-offset-orange-300 sm:text-sm">
          <span className="block truncate">{selected?.name || 'Select a brand'}</span>
          <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
            <ChevronUpDownIcon
              className="h-5 w-5 text-gray-400"
              aria-hidden="true"
            />
          </span>
        </Listbox.Button>
        <Transition
          as={Fragment}
          leave="transition ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <Listbox.Options className="absolute mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
            {brands.map((brand) => (
              <Listbox.Option
                key={brand.id}
                className={({ active }) =>
                  `relative cursor-default select-none py-2 pl-10 pr-4 ${
                    active ? 'bg-amber-100 text-amber-900' : 'text-gray-900'
                  }`
                }
                value={brand}
              >
                {({ selected }) => (
                  <>
                    <span
                      className={`block truncate ${
                        selected ? 'font-medium' : 'font-normal'
                      }`}
                    >
                      {brand.name}
                    </span>
                    {selected ? (
                      <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-600">
                        <CheckIcon className="h-5 w-5" aria-hidden="true" />
                      </span>
                    ) : null}
                  </>
                )}
              </Listbox.Option>
            ))}
          </Listbox.Options>
        </Transition>
      </div>
    </Listbox>
  )
}