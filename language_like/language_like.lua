local export = {}

local insert = table.insert
local ipairs = ipairs
local type = type

local function flatten_data(data, t)
	for _, v in ipairs(data) do
		if type(v) == "table" then
			flatten_data(v, t)
		else
			insert(t, v)
		end
	end
	return t
end

-- Implementation of getOtherNames() for languages, etymology languages,
-- families and scripts. If `onlyOtherNames` is passed in, only return
-- the names in the `otherNames` field, otherwise combine `otherNames`,
-- `aliases` and `varieties`.
function export.getOtherNames(self, onlyOtherNames)
	local data
	if self._extraData then
		data = self._extraData
	elseif self._rawData then
		data = self._rawData
	else
		-- Called from [[Module:list of languages]]; fields already available directly.
		data = self
	end
	if onlyOtherNames then
		return data.otherNames or {}
	end
	local ret, otherNames, aliases, varieties = {}, data.otherNames, data.aliases, data.varieties
	if otherNames then
		flatten_data(otherNames, ret)
	end
	if aliases then
		flatten_data(aliases, ret)
	end
	if varieties then
		flatten_data(varieties, ret)
	end
	return ret
end


-- Implementation of getVarieties() for languages, etymology languages,
-- families and scripts. If `flatten` is passed in, flatten down to a
-- list of strings; otherwise, keep the structure.
function export.getVarieties(self, flatten)
	local data
	if self._extraData then
		data = self._extraData
	elseif self._rawData then
		data = self._rawData
	else
		-- Called from [[Module:list of languages]]; fields already available directly.
		data = self
	end
	local varieties = data.varieties
	if not varieties then
		return {}
	-- If flattening not requested, just return them.
	elseif not flatten then
		return varieties
	end
	return flatten_data(varieties, {})
end


-- Implementation of template-callable getByCode() function for languages,
-- etymology languages, families and scripts. `item` is the language,
-- family or script in question; `args` is the arguments passed in by the
-- module invocation; `extra_processing`, if specified, is a function of
-- one argument (the requested property) and should return the value to
-- be returned to the caller, or nil if the property isn't recognized.
-- `extra_processing` is called after special-cased properties are handled
-- and before general-purpose processing code that works for all string
-- properties.
function export.templateGetByCode(args, extra_processing)
	-- The item that the caller wanted to look up.
	local item, itemname, list = args[1], args[2]
	if itemname == "getOtherNames" then
		list = item:getOtherNames()
	elseif itemname == "getOnlyOtherNames" then
		list = item:getOtherNames(true)
	elseif itemname == "getAliases" then
		list = item:getAliases()
	elseif itemname == "getVarieties" then
		list = item:getVarieties(true)
	end
	if list then
		local index = args[3]; if index == "" then index = nil end
		index = tonumber(index or error("Numeric index of the desired item in the list (parameter 3) has not been specified."))
		return list[index] or ""
	end

	if itemname == "getFamily" and item.getFamily then
		return item:getFamily():getCode()
	end

	if extra_processing then
		local retval = extra_processing(itemname)
		if retval then
			return retval
		end
	end

	if item[itemname] then
		local ret = item[itemname](item)
		
		if type(ret) == "string" then
			return ret
		else
			error("The function \"" .. itemname .. "\" did not return a string value.")
		end
	end

	error("Requested invalid item name \"" .. itemname .. "\".")
end

-- Implementation of getCommonsCategory() for languages, etymology languages,
-- families and scripts.
function export.getWikidataItem(self)
	local item = self._WikidataItem
	if item == nil then
		item = self._rawData[2]
		-- If the value is nil, it's cached as false.
		item = item ~= nil and (type(item) == "number" and "Q" .. item or item) or false
		self._WikidataItem = item
	end
	return item or nil
end

-- Implementation of getWikipediaArticle() for languages, etymology languages,
-- families and scripts.
function export.getWikipediaArticle(self, noCategoryFallback, project)
	if not project then
		project = "enwiki"
	end
	local cached_value
	if project == "enwiki" then
		cached_value = self._wikipedia_article
		if cached_value == nil then
			cached_value = self._rawData.wikipedia_article
		end
	else
		-- If the project isn't enwiki, default to no category fallback, but
		-- this can be overridden by specifying the value `false`.
		if noCategoryFallback == nil then
			noCategoryFallback = true
		end
		local non_en_wikipedia_articles = self._non_en_wikipedia_articles
		if non_en_wikipedia_articles == nil then
			self._non_en_wikipedia_articles = {}
		else
			cached_value = non_en_wikipedia_articles[project]
		end
	end
	if cached_value == nil then -- not false
		local item = self:getWikidataItem()
		if item and mw.wikibase then
			cached_value = mw.wikibase.sitelink(item, project)
		end
		if not cached_value then
			cached_value = false
		end
		-- Cache the determined value.
		if project == "enwiki" then
			self._wikipedia_article = cached_value
		else
			self._non_en_wikipedia_articles[project] = cached_value
		end
	end
	if cached_value or noCategoryFallback then
		return cached_value or nil
	end
	return (self:getCategoryName():gsub("Creole language", "Creole"))
end

do
	local function get_commons_cat_claim(item)
		if item then
			local entity = mw.wikibase.getEntity(item)
			if entity then
				-- P373 is the "Commons category" property.
				local claim = entity:getBestStatements("P373")[1]
				return claim and ("Category:" .. claim.mainsnak.datavalue.value) or nil
			end
		end
	end
	
	local function get_commons_cat_sitelink(item)
		if item then
			local sitelink = mw.wikibase.sitelink(item, "commonswiki")
			-- Reject any sitelinks that aren't categories.
			return sitelink and sitelink:match("^Category:") and sitelink or nil
		end
	end
	
	-- Implementation of getCommonsCategory() for languages, etymology
	-- languages, families and scripts.
	function export.getCommonsCategory(self)
		local cached_value
		cached_value = self._commons_category
		if cached_value ~= nil then -- including false
			return cached_value or nil
		elseif not mw.wikibase then
			cached_value = false
			return nil
		end
		-- Checks are in decreasing order of likelihood for a useful match.
		-- Get the Commons Category claim from the language's item.
		local lang_item = self:getWikidataItem()
		cached_value = get_commons_cat_claim(lang_item)
		if cached_value == nil then
			-- Otherwise, try the language's category's item.
			local langcat_item = mw.wikibase.getEntityIdForTitle("Category:" .. self:getCategoryName())
			cached_value = get_commons_cat_claim(langcat_item)
			if cached_value == nil then
				-- If there's no P373 claim, there might be a sitelink on the
				-- language's category's item.
				cached_value = get_commons_cat_sitelink(langcat_item)
				if cached_value == nil then
					-- Otherwise, try for a sitelink on the language's own item.
					cached_value = get_commons_cat_sitelink(lang_item)
					if cached_value == nil then
						cached_value = false
					end
				end
			end
		end
		self._commons_category = cached_value
		return cached_value or nil
	end
end

return export