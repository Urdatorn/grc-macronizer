mw = {}

-- Mock mw.ustring for Unicode string operations
mw.ustring = {
    sub = function(s, i, j) return string.sub(s, i, j) end,
    find = function(s, pattern) return string.find(s, pattern) end,
    toNFD = function(s) return s end,  -- Simplified: return input unchanged
}

-- Mock mw.loadData to load preprocessed data
mw.loadData = function(path)
    local file_path = path:gsub("%.", "/") .. ".lua"
    local data = dofile(file_path)  -- Load Lua file
    return data
end