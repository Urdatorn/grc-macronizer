-- Transclusion-based tracking as subpages of [[Wiktionary:Tracking]].
-- Tracked pages can be found at [[Special:WhatLinksHere/Wiktionary:Tracking/KEY]].
local error = error
local find = string.find
local makeTitle = mw.title.makeTitle
local sub = string.sub
local type = type

local memo = {}

local function track(key)
	-- Return if memoized.
	if memo[key] then
		return
	end
	-- Throw an error if `key` isn't a string.
	local key_type = type(key)
	if key_type ~= "string" then
		error("Tracking keys supplied to [[Module:debug/track]] must be strings; received " .. key_type .. ".", 3)
	end
	-- makeTitle returns nil for invalid titles, but "#" is treated as a
	-- fragment separator (e.g. "foo#bar" generates the title "foo"), so we
	-- need to manually exclude it.
	local title = not find(key, "#", 1, true) and makeTitle(4, "Tracking/" .. key)
	if title then
		-- Normalize the key, by getting title.text and removing the initial
		-- "Tracking/". Normally this will be the same as title.subpageText,
		-- but subpageText will be wrong if there are further slashes, so we
		-- can't use it.
		local normalized = sub(title.text, 10)
		-- Return if the normalized form has been memoized.
		if memo[normalized] then
			return
		end
		-- Otherwise, transclude the page. Getting the raw page content is the
		-- fastest way to trigger transclusion, as it avoids any parser
		-- expansion of the target page.
		title:getContent()
		-- Memoize normalized form.
		memo[normalized] = true
	else
		-- Track uses of invalid keys. Replace with error message once all have
		-- been eliminated.
		-- [[Special:WhatLinksHere/Wiktionary:Tracking/debug/track/invalid key]]
		track("debug/track/invalid key")
		-- error("Tracking key \"" .. key .. "\" supplied to [[Module:debug/track]] is invalid: key must be a [[mw:Help:Bad title|valid page name]].", 3)
	end
	memo[key] = true
end

return function(input)
	if input == nil then
		error("No tracking key supplied to [[Module:debug/track]].", 2)
	elseif type(input) ~= "table" then
		track(input)
		return true
	end
	local key = input[1]
	if key == nil then
		error("No tracking keys in table supplied to [[Module:debug/track]].", 2)
	end
	local i = 1
	repeat
		track(key)
		i = i + 1
		key = input[i]
	until key == nil
	return true
end