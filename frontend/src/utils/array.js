function objectToFlat(obj, root_key = '') {
  const params = {}
  for (const key in obj) {
    const value = obj[key]
    if (typeof value === 'object' && !Array.isArray(value)) {
      const newKey = root_key ? `${root_key}.${key}` : key
      Object.assign(params, objectToFlat(value, newKey))
    } else {
      const newKey = root_key ? `${root_key}.${key}` : key
      params[newKey] = value
    }
  }
  return params
}

function flatToObject(obj) {
  const result = {}

  function assign(current, keys, value) {
    const [first, ...rest] = keys

    if (!rest.length) {
      if (
        typeof value === 'object' &&
        value !== null &&
        !Array.isArray(value)
      ) {
        current[first] = {
          ...(current[first] || {}),
          ...value
        }
      } else {
        current[first] = value
      }
      return
    }

    if (
      !current[first] ||
      typeof current[first] !== 'object' ||
      Array.isArray(current[first])
    ) {
      current[first] = {}
    }

    assign(current[first], rest, value)
  }

  for (const key in obj) {
    const value = obj[key]
    if (typeof key === 'string' && key.includes('.')) {
      assign(result, key.split('.'), value)
    } else {
      assign(result, [key], value)
    }
  }

  return result
}


export {
  objectToFlat,
  flatToObject
}
