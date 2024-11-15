local function file_exists(name)
    local f = io.open(name, "r")
    if f then
        f:close()
        return true
    else
        return false
    end
end

local function check_require(module_path)
    -- Translate the MediaWiki-style path to a local file path
    local local_path = module_path:gsub("^Module:", ""):gsub("%.", "/") .. ".lua"
    print("Checking module:", local_path)
    if not file_exists(local_path) then
        error("Required module not found: " .. local_path)
    end
    return module_path
end

-- Mock require with checks
local original_require = require
require = function(module_path)
    check_require(module_path)
    return original_require(module_path)
end

-- Enhanced error handling
local function error_handler(err)
    return debug.traceback("Error: " .. tostring(err), 2)
end

-- Test script
local function run_test()
    require("mw")  -- Load the mock MediaWiki functions
    local grc_conj = require("grc-conj")

    -- Example input for λύω
    local input = {
        lemma = "λύω",
        inflection_type = "luō"
    }

    -- Call the conjugation function
    local result = grc_conj.generate(input)

    print(result)  -- Display the conjugation table
end

local status, err = xpcall(run_test, error_handler)

if not status then
    print(err)
end