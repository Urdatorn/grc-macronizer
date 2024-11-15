mw = mw or {}

-- Mock mw.uri for URL-related functions
mw.uri = {
    anchorEncode = function(text)
        return text:gsub(" ", "_")  -- Example implementation
    end
}

-- Mock mw.text for text operations
mw.text = {
    nowiki = function(text) return text end,
    trim = function(text) return text:match("^%s*(.-)%s*$") end,
    split = function(text, delimiter)
        local result = {}
        for match in (text .. delimiter):gmatch("(.-)" .. delimiter) do
            table.insert(result, match)
        end
        return result
    end,
    unstrip = function(text)
        return text  -- Simplified mock
    end
}

-- Mock mw.text.gsplit for gmatch iterator
mw.text.gsplit = function(s, delimiter)
    local result = {}
    for match in (s .. delimiter):gmatch("(.-)" .. delimiter) do
        table.insert(result, match)
    end
    return ipairs(result)
end

-- Mock mw.ustring for Unicode string operations
mw.ustring = {
    sub = function(s, i, j) return string.sub(s, i, j) end,
    find = function(s, pattern) return string.find(s, pattern) end,
    toNFD = function(s) return s end,  -- Simplified: return input unchanged
    toNFC = function(s) return s end  -- Simplified: return input unchanged
}

-- Mock mw.loadData to load preprocessed data
mw.loadData = function(path)
    local file_path = path:gsub("%.", "/") .. ".lua"
    local data = dofile(file_path)  -- Load Lua file
    return data
end

-- Mock mw.title for title-related functions
mw.title = {
    new = function(title)
        return {text = title, exists = true}  -- Simplified mock
    end
}

-- Additional mocks to handle other dependencies
mw.site = {
    namespaces = function()
        return {}  -- Simplified: empty table
    end
}

mw.message = {
    new = function(msg)
        return {plain = msg}  -- Simplified mock
    end
}

-- Mock mw.debug for tracking/debugging functions
mw.debug = {
    track = function(event)
        print("Debug Track:", event)  -- Simplified debug tracking
    end
}