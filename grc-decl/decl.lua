local module_path = 'Module:grc-decl/decl'

local m_classes = mw.loadData(module_path .. '/classes')
local m_paradigms = mw.loadData(module_path .. '/staticdata/paradigms')
local m_dialect_groups = mw.loadData(module_path .. '/staticdata/dialects')
local m_decl_data = require(module_path .. '/data')
local m_accent = require('grc-accent')

local usub = mw.ustring.sub
local decompose = mw.ustring.toNFD
local compose = mw.ustring.toNFC

-- Equivalent to mw.ustring.len.
local function ulen(str)
	local _, length = string.gsub(str, '[\1-\127\194-\244][\128-\191]*', '')
	return length
end

-- Basic string functions can be used when there are no character sets or
-- quantifiers.
local ufind = mw.ustring.find
local ugsub = mw.ustring.gsub

local export = {
	inflections = m_decl_data.inflections,
	adjinflections = m_decl_data.adjinflections,
	adjinflections_con = m_decl_data.adjinflections_con,
}

local function quote(text)
	return "“" .. text .. "”"
end

local function get_accent_info(form)
	-- Get position of accent (nth vowel from beginning of word).
	local accent = {}
	local is_suffix = form:sub(1, 1) == '-'
	accent.position, accent.type = m_accent.detect_accent(form)
	-- Position: position of accent from beginning of word (number) or nil.
	-- Accent: accent name (string) or nil.
	
	-- Form must have an accent, unless it is a suffix.
	if not is_suffix and not next(accent) then
		error('No accent detected on ' .. quote(form) ..
				'. Please add an accent by copying this template and placing ' ..
				quote('/') .. ' for acute or ' .. quote('~') ..
				' for circumflex after the vowel that should be accented: {{subst:chars|grc|' .. form .. '}}.')
	end
	
	-- Accent term as proxy for distinguishing between oxytone and perispomenon.
	accent.term = m_accent.get_accent_term(form)
	
	return accent, is_suffix
end

local form_redirects = {
	AS = 'NS', VS = 'NS',
	DD = 'GD', AD = 'ND', VD = 'ND',
	AP = 'NP', VP = 'NP',
}

local form_metatable = {
	__index = function (self, form_code)
		if type(form_code) ~= 'string' then return nil end
		if form_redirects[form_code] then
			return self[form_redirects[form_code]]
		elseif form_redirects[form_code:sub(2)] then
			return self[form_code:sub(1, 1) .. form_redirects[form_code:sub(2)]]
		-- If this is a neuter form but not in the nominative case,
		-- use the corresponding masculine form.
		elseif form_code:match('N[^N].') then
			return self['M' .. form_code:sub(2)]
		end
	end,
}

local function add_redirects(form_table)
	return setmetatable(form_table, form_metatable)
end

local function add_forms(args)
	if not args.irregular then
		--add stem to forms
		local function add_stem(forms)
			return forms:gsub('%$', args.stem)
		end
		
		-- args.suffix indicates that this is a paradigm for an unaccented suffix,
		-- such as [[-εια]].
		if args.indeclinable then
			for k, v in pairs(args.ctable) do
				if k:find('[NGDAV][SDP]') then -- only format case-number forms
					args.ctable[k] = args[2]
				end
			end
		elseif args.suffix and not next(args.accent) then
			for k, v in pairs(args.ctable) do
				if k:find('[NGDAV][SDP]') then -- only format case-number forms
					args.ctable[k] = add_stem(v)
				end
			end
		else
			-- If the term is not a suffix and no accent was detected, then
			-- get_accent_info above must throw an error,
			-- or else there will be an uncaught error here.
			local add_circumflex = args.accent.type == 'circumflex'
			local recessive = -3
			
			-- Force recessive accent in the Lesbian dialect.
			local accent_position = args.dial == 'les' and recessive
					or args.accent.position
			
			-- Circumflex on monosyllabic DS and AS in consonant-stem third-
			-- declension nouns: for example, Τρῷ and Τρῶ, DS and AS of Τρώς.
			local DS_AS = args.accent_alternating == true
			
			-- Added by "kles" function: for example, Περίκλεις.
			local VS = args.recessive_VS and recessive
			local synaeresis = args.synaeresis
			
			local add_accent = m_accent.add_accent
			local function add_accent_to_forms(forms, code)
				return ugsub(forms,
					'[^/]+',
					function(form)
						return add_accent(form,
							code == 'VS' and VS or accent_position,
							{
								synaeresis = synaeresis,
								circumflex = (code == 'DS' or code == 'AS') and DS_AS or add_circumflex,
								short_diphthong = true,
								force_antepenult = args.force_antepenult,
							})
					end)
			end
			
			for k, v in pairs(args.ctable) do
				if k:find('[NGDAV][SDP]') then -- only format case-number forms
					args.ctable[k] = add_accent_to_forms(add_stem(v), k)
				end
			end
		end
	end
end

local gender_codes = { 'M', 'F', 'N' }
local case_codes = { 'N', 'G', 'D', 'A', 'V' }
local number_codes = { 'S', 'D', 'P' }
local function handle_noun_overrides(form_table, override_table)
	for _, case in ipairs(case_codes) do
		for _, number in ipairs(number_codes) do
			local key = case .. number
			if override_table[key] then 
				require('debug').track('grc-decl/form-override')
			end
			form_table[key] = override_table[key] or form_table[key]
		end
	end
end

local function handle_adjective_overrides(form_table, override_table)
	for _, gender in ipairs(gender_codes) do
		for _, case in ipairs(case_codes) do
			for _, number in ipairs(number_codes) do
				local key = gender .. case .. number
				if override_table[key] then 
					require('debug').track('grc-adecl/form-override')
				end
				form_table[key] = override_table[key] or form_table[key]
			end
		end
	end
end

--[=[
	Gets stem-ending combinations from [[Module:grc-decl/decl/data]]
	and [[Module:grc-decl/decl/staticdata]]. Called a single time to get forms
	of a noun, and two or three times by make_decl_adj for each of the genders
	of an adjective.
]=]
function export.make_decl(args, decl, root, is_adjective)
	if not export.inflections[decl] then
		error('Inflection type ' .. quote(decl) .. ' not found in [[' .. module_path .. "/data]].")
	end
	if args.adjective and args.irregular then
		error('Irregular adjectives are not handled by make_decl.')
	end
	
	if not root then
		error('No root for ' .. args[1] .. '.')
	end
	args.stem = root
	
	export.inflections[decl](args)
	args.gender[1] = args.gender[1] or args.ctable['g']
	args.declheader = args.declheader or args.ctable['decl']
	add_forms(args)
	if not is_adjective then
		handle_noun_overrides(args.ctable, args)
	end
	add_redirects(args.ctable)
end

-- String (comparative ending), function (input: root; output: comparative),
-- false (the declension has no comparative form), or nil (use the if-statements
-- to determine a comparative form).
local decl_to_comp = {
	['1&3-ᾰν'] = 'ᾰ́ντερος',
	['1&3-εν'] = 'έντερος',
	['1&3-εσσ'] = 'έστερος', -- hopefully this is general?
	['1&3-ups'] = 'ῠ́τερος',
	['3rd-cons'] = function(root)
		local last2 = usub(root, -2)
		if last2 == 'ον' then
			return root .. 'έστερος'
		elseif last2 == 'εσ' then
			return root:gsub('εσ$', 'έστερος')
		else
			return false
		end
	end,
	['1&3-οτ'] = false,
	['3rd-εσ'] = 'έστερος',
	['3rd-εσ-open'] = 'έστερος',
	['1&2-alp-con'] = 'εώτερος', -- I assume—though I can't find examples
	['1&2-eta-con'] = 'εώτερος',
}

local function retrieve_comp(root, decl_type)
	local data = decl_to_comp[decl_type]
	if not data then
		return data
	elseif type(data) == 'string' then
		return root .. data
	elseif type(data) == 'function' then
		return data(root)
	else
		error('Data for ' .. decl_type .. ' is invalid.')
	end
end

-- Constructs an adverb, comparative, and superlative.
function export.make_acs(args)
	-- input:
	-- strings
	local root, decl_type = args.root, args.decl_type
	-- tables
	local accent, atable = args.accent, args.atable
	-- output:
	local comp = retrieve_comp(root, decl_type)
	local super, adv
	
	if comp == nil then
		local alpha_nonultima = decl_type == '1&2-alp' and
				accent.term ~= 'oxytone' and
				accent.term ~= 'perispomenon'
		local last3 = usub(root, -3)
		if alpha_nonultima and last3 == 'τερ' then
			comp = '(' .. atable['MNS'] .. ')'
			adv = atable['NNS']
			-- ?
			-- comp = nil
		elseif alpha_nonultima and last3 == 'τᾰτ' then
			super = '(' .. atable['MNS'] .. ')'
			adv = atable['NNP']
			-- ?
			-- super = nil
		elseif decl_type:find('ντ') then
			comp = nil -- participles
			super = nil
		elseif (m_accent.get_weight(root, 1) == "light" or decl_type:find('att$')) then
			comp = root .. 'ώτερος'
		else
			comp = root .. 'ότερος'
		end
	end
	atable.adv = adv
		-- Actually neuter accusative singular. This is correct for -τερος and
		-- for μείζων; also for all comparatives in -ων?
		or args.comparative and atable.NNS
		-- actually neuter accusative plural
		or args.superlative and atable.NNP
		or atable.MGP and atable.MGP:gsub('ν$', 'ς'):gsub('ν<', 'ς<')
	atable.comp = comp
	atable.super = super or comp and comp:gsub('ερος$', 'ᾰτος')
	
	-- Remove comparative and superlative if adjective is a comparative or superlative.
	-- Parameters that trigger this condition are |deg=comp, |deg=super, and the
	-- deprecated |form=comp.
	if args.comparative or args.superlative then
		atable.comp, atable.super = nil, nil
	end
	
	for _, form in ipairs { 'adv', 'comp', 'super' } do
		if args[form] == "-" then
			atable[form] = nil
		elseif args[form] then
			atable[form] = args[form]
		end
	end
end

--[[
	noun_table contains case-number forms.
	adjective_table will contain gender-case-number forms.
	override_table contains gender-case-number forms that will override the
	forms in noun_table.
]]
local function transfer_forms_to_adjective_table(adjective_table, noun_table, gender_code)
	for case_and_number_code, form in pairs(noun_table) do
		adjective_table[gender_code .. case_and_number_code] = form
	end
end

--[=[
	Interprets the table for the adjective's inflection type
	in [[Module:grc-decl/decl/staticdata]].
]=]
function export.make_decl_adj(args, ct)
	if args.irregular then
		return export.inflections['irreg-adj'](args)
	end
	
	--[[
		Two possibilities, with the indices of the table of endings
		and the stem augmentation that they use:
			- masculine–feminine (1, a1), neuter (2, a2)
			- masculine (1, a1), feminine (2, a2), neuter (3, a1)
	]]
	-- Masculine or masculine and feminine forms.
	export.make_decl(args, ct[1], args.root .. (ct.a1 or ''), true)
	transfer_forms_to_adjective_table(args.atable, args.ctable, 'M')
	
	-- Feminine or neuter forms.
	if ct[2] then
		export.make_decl(args, ct[2], args.fstem or (args.root .. (ct.a2 or '')), true)
		transfer_forms_to_adjective_table(args.atable, args.ctable, 'F')
	end
	
	export.make_decl(args, ct[3], args.root .. (ct.a1 or ''), true)
	transfer_forms_to_adjective_table(args.atable, args.ctable, 'N')
	
	add_redirects(args.atable)
	args.ctable = nil
	export.make_acs(args)
	handle_adjective_overrides(args.atable, args)
	args.adeclheader = ct.adeclheader or 'Declension'
end

-- This function requires NFC forms for [[Module:grc-decl/decl/classes]],
-- but NFD forms for [[Module:grc-decl/decl/data]].
function export.get_decl(args)
	if args.indeclinable then
		if not args[2] then error("Specify the indeclinable form in the 2nd parameter.") end
		args.decl_type, args.root = 'indecl', ''
		return
	elseif args.irregular then
		if args.gender[1] == "N" then
			args.decl_type, args.root = 'irregN', ''
		else
			args.decl_type, args.root = 'irreg', ''
		end
		return
	elseif not (args[1] and args[2]) then
		error("Use the 1st and 2nd parameters for the nominative and genitive singular.")
	end
	
	local infl_info = m_classes.infl_info.noun
	
	args[1] = compose(args[1])
	args[2] = compose(args[2])
	
	local arg1, arg2 = args[1], args[2]
	
	local nom_without_accent = compose(m_accent.strip_tone(arg1))
	local gen_without_accent = compose(m_accent.strip_tone(arg2))
	
	local decl_types_by_genitive_ending, decl_type, root
	local nominative_matches = {}
	for i = -infl_info.longest_nominative_ending, -1 do
		local nominative_ending = usub(nom_without_accent, i)
		local decl_types_by_genitive_ending = infl_info[nominative_ending]
		-- If decl_types_by_genitive_ending is a string, then it is the key of
		-- another table in infl_info, a nominative ending with a macron or
		-- breve (ι → ῐ).
		if type(decl_types_by_genitive_ending) == "string" then
			decl_types_by_genitive_ending = infl_info[decl_types_by_genitive_ending]
		end
		
		if decl_types_by_genitive_ending then
			table.insert(nominative_matches, decl_types_by_genitive_ending)
			root = usub(nom_without_accent, 1, -1 - ulen(nominative_ending))
			
			for i = -6, -1 do
				local genitive_ending = usub(gen_without_accent, i)
				local name = decl_types_by_genitive_ending[genitive_ending]
				if name then
					decl_type = name
					break
				end
			end
			
			if decl_type then
				break
			end
		end
	end
	
	args.accent, args.suffix = get_accent_info(arg1)
	
	if decl_type and root then
		if args.contracted == 'false' and not decl_type:find('open') then
			decl_type = decl_type .. '-open'
		end
		args.decl_type, args.root = decl_type, decompose(root)
		
		return
	elseif gen_without_accent:find('ος$') then
		local root = decompose(usub(gen_without_accent, 1, -3))
		if args.gender[1] == "N" or ufind(root, 'α[̆̄]τ$') and not (args.gender[1] == "M" and args.gender[2] == "F") then
			args.decl_type, args.root = '3rd-N-cons', root
		else
			args.decl_type, args.root = '3rd-cons', root
		end
		
		return
	end
	
	if nominative_matches[1] then
		local m_table = require 'Module:table'
		local fun, grc =
			require 'Module:fun', require 'Module:languages'.getByCode 'grc'
		local make_sort_key = fun.memoize(
			function (term)
				return (grc:makeSortKey(term))
			end)
		
		if nominative_matches[2] then
			local new_nominative_matches = {}
			for _, matches in ipairs(nominative_matches) do
				for k, v in pairs(matches) do
					new_nominative_matches[k] = v
				end
			end
			nominative_matches = new_nominative_matches
		else
			nominative_matches = nominative_matches[1]
		end
		
		local gens = require 'Module:fun'.map(
			function (gen)
				return quote("-" .. gen)
			end,
			m_table.keysToList(
				nominative_matches,
				function (gen1, gen2)
					local sort_key1, sort_key2 =
						make_sort_key(gen1), make_sort_key(gen2)
					if sort_key1 == sort_key2 then
						return gen1 < gen2
					else
						return sort_key1 < sort_key2
					end
				end))
		
		local agreement
		if #gens > 1 then
			agreement = { "Declensions were", "s ", " do" }
		else
			agreement = { "A declension was", " ", " does" }
		end
		gens = table.concat(gens, ", ")
		
		error(agreement[1] .. " found that matched the ending of the nominative form " .. quote(arg1) ..
				", but the genitive ending" .. agreement[2] .. gens ..
				agreement[3] .. " not match the genitive form " .. quote(arg2) .. ".")
	else
		for nom, gens in pairs(m_classes.ambig_forms) do
			if arg1:find(nom .. "$") then
				for gen, _ in pairs(gens) do
					if arg2:find(gen .. "$") then
						error("No declension found for nominative " .. quote(arg1) .. " and genitive " .. quote(arg2) ..
								". There are two declensions with nominative " .. quote("-" .. nom) ..
								" and genitive " .. quote("-" .. gen) ..
								". To indicate which one you mean, mark the vowel length of the endings with a macron or breve.")
					end
				end
			end
		end
		
		error("Can’t find a declension type for nominative " .. quote(arg1) .. " and genitive " .. quote(arg2) .. ".")
	end
end

-- This function requires NFC forms for [[Module:grc-decl/decl/classes]],
-- but NFD forms for [[Module:grc-decl/decl/data]].
function export.get_decl_adj(args)
	if args.irregular then
		args.decl_type, args.root = 'irreg', ''
		return
	elseif not args[1] then
		error('Use the 1st and 2nd parameters for the masculine and the ' ..
			'feminine or neuter nominative singular, or the first parameter ' ..
			' alone for the 3rd declension stem.')
	end
	
	args[1] = compose(args[1])
	if args[2] then
		args[2] = compose(args[2])
	end
	
	local arg1, arg2 = args[1], args[2]
	
	local mstrip = compose(m_accent.strip_tone(arg1))
	local fstrip
	if arg2 then
		fstrip = compose(m_accent.strip_tone(arg2))
	else
		args.accent, args.suffix = get_accent_info(arg1)
		
		args.decl_type, args.root = '3rd-cons', decompose(mstrip)
		
		return
	end
	
	local infl_info = m_classes.infl_info.adj
	
	-- See if last three or two characters of masc have an entry.
	local masc, decl
	for i = -infl_info.longest_masculine_ending, -2 do
		local ending = usub(mstrip, i)
		local data = infl_info[ending]
		if data then
			masc = ending
			decl = data
			break
		end
	end
	
	-- Allows redirecting, so that macrons or breves can be omitted for instance.
	if type(decl) == "string" then
		decl = infl_info[decl]
	end
	
	if decl then
		-- Look for a feminine ending that matches the end of the feminine form.
		local fem, name
		for feminine, decl_name in pairs(decl) do
			if fstrip:find(feminine .. '$') then
				fem = feminine
				name = decl_name:gsub("%d$", "")
				break
			end
		end
		
		if fem then
			args.accent, args.suffix = get_accent_info(arg1)
			
			-- The only indication that λέγων, λέγουσᾰ (stem λεγοντ-) and
			-- ποιῶν, ποιοῦσᾰ (stem ποιουντ-) have different stems is the
			-- accentuation of the masculine form.
			if name == '1&3-οντ' and args.accent.term == 'perispomenon' then
				name = '1&3-οντ-con'
			end
			
			if not export.adjinflections[name] then
				error('Inflection recognition failed. Function for generated inflection code ' ..
						quote(name) .. ' not found in [[' .. module_path .. "/data]].")
			end
			
			args.decl_type, args.root = name, decompose(mstrip:gsub(masc .. "$", ""))
			
			return
		else
			-- No declension type found.
			local fems = {}
			local is_neuter = false
			for fem in pairs(decl) do
				if fem == "ον" then
					is_neuter = true
				end
				table.insert(fems, quote("-" .. fem))
			end
			fems = table.concat(fems, ", ")
			local agreement = { "A declension was", " ", " does" }
			if #fems > 1 then
				agreement = { "Declensions were", "s ", " do" }
			end
			error(agreement[1] .. " found that matched the ending of the masculine " .. quote(arg1) ..
					", but the corresponding feminine" .. (is_neuter and " and neuter" or "") .. " ending" .. agreement[2] .. fems ..
					agreement[3] .. " not match the feminine " .. quote(arg2) .. ".")
		end
	end
	error("Can’t find a declension type for masculine " .. quote(arg1) .. " and feminine or neuter " .. quote(arg2) .. ".")
end

--[[
	Returns a table containing the inflected forms of the article,
	to be placed before each inflected noun form.
]]
function export.infl_art(args)
	if args.dial == 'epi' or args.adjective or args.no_article then
		return {}
	end
	
	local art = {}
	local arttable
	
	if args.gender[1] then
		arttable = m_paradigms.art_att[args.gender[1]]
	else
		error('Gender not specified.')
	end
	for code, suffix in pairs(arttable) do
		if (args.gender[1] == "M" and args.gender[2] == "F") and
				m_paradigms.art_att.M[code] ~= m_paradigms.art_att.F[code] then
			art[code] = m_paradigms.art_att.M[code] .. ', ' .. m_paradigms.art_att.F[code]
		else
			art[code] = suffix
		end
	end
	
	if args.gender[1] == 'F' then
		if m_dialect_groups['nonIA'][args.dial] then
			art['NS'] = 'ᾱ̔' -- 104.1-4
			art['GS'] = 'τᾶς'
			art['DS'] = 'τᾷ'
			art['AS'] = 'τᾱ̀ν'
		end
		
		if args.dial == 'the' or args.dial == 'les' then
			art['DS'] = 'τᾶ' -- 39
		elseif args.dial == 'boi' or args.dial == 'ara' or args.dial == 'ele' then
			art['DS'] = 'ται' -- 104.3
		end
		
		if m_dialect_groups['nonIA'][args.dial] then
			art['GP'] = 'τᾶν' -- 104.6
		end
		
		if args.dial == 'ato' then
			art['DP'] = 'τῆσῐ(ν)' -- 104.7
		elseif args.dial == 'ion' then
			art['DP'] = 'τῇσῐ(ν)' -- 104.7
		end
		
		if m_dialect_groups['buck78'][args.dial] then
			art['AP'] = 'τᾰ̀ς' -- 104.8
		elseif args.dial == 'kre' or args.dial == 'arg' then
			art['AP'] = 'τὰνς'
		elseif args.dial == 'les' then
			art['AP'] = 'ταῖς'
		elseif args.dial == 'ele' then
			art['AP'] = 'ταὶρ'
		end
		
		if args.dial == 'kre' or args.dial == 'les' or args.dial == 'kyp' then
			art['NS'] = 'ᾱ̓' -- 57
			art['NP'] = 'αἰ'
		elseif args.dial == 'ele' then
			art['NS'] = 'ᾱ̓'
			art['NP'] = 'ταὶ'
		elseif args.dial == 'boi' then
			art['NP'] = 'τὴ' -- 104.5
		elseif m_dialect_groups['west'][args.dial] then --boeotian is covered above
			art['NP'] = 'ταὶ'
		end
	elseif args.gender[1] == 'M' or args.gender[1] == 'N' then
		if args.dial == 'the' then
			art['GS'] = 'τοῖ' -- 106.1
			art['DS'] = 'τοῦ' -- 23
			art['ND'] = 'τοὺ'
			art['GP'] = 'τοῦν'
		end
		
		if args.dial == 'les' then
			art['DS'] = 'τῶ' -- 106.2
		elseif args.dial == 'boi' or args.dial == 'ara' or args.dial == 'ele' or args.dial == 'eub' then
			art['DS'] = 'τοι' -- 106.2
		end
		
		if args.dial == 'ato' or args.dial == 'ion' then
			art['DP'] = 'τοῖσῐ(ν)' -- 106.4
		end
		
		if args.gender[1] == 'M' then
			if m_dialect_groups['buck78'][args.dial] then
				art['AP'] = 'τὸς' -- 106.5
			elseif args.dial == 'kre' or args.dial == 'arg' then
				art['AP'] = 'τὸνς'
			elseif args.dial == 'les' then
				art['AP'] = 'τοῖς'
			elseif args.dial == 'ele' then
				art['AP'] = 'τοὶρ'
			elseif m_dialect_groups['severe'][args.dial] or args.dial == 'boi' then
				art['AP'] = 'τὼς'
			end
			
			if args.dial == 'kre' or args.dial == 'les' or args.dial == 'kyp' then
				art['NS'] = 'ὀ' -- 57
				art['NP'] = 'οἰ'
			elseif args.dial == 'ele' then
				art['NS'] = 'ὀ'
				art['NP'] = 'τοὶ'
			elseif m_dialect_groups['west'][args.dial] or args.dial == 'boi' then
				art['NP'] = 'τοὶ'
			end
		end
		
		if args.dial == 'ele' then
			art['GD'] = 'τοίοις'
			--		elseif args.dial == 'ara' then
			--			art['GD'] = 'τοιυν'
		end
	end
	
	return art
end
	
local lang = require('languages').getByCode("grc")
local function tag(text)
	return require('Module:script utilities').tag_text("-" .. text, lang)
end

local function print_detection_table(detection_table, labels, noun)
	local out = require('array')()
	
	local function sort(item1, item2)
		-- Put 'longest_nominative_ending' and 'longest_masculine_ending' first.
		if item1:find '^longest' or item2:find '^longest' then
			return item1:find '^longest' ~= nil
		end
		
		local sort1, sort2 = (lang:makeSortKey(item1)), (lang:makeSortKey(item2))
		local decomp_length1, decomp_length2 = ulen(decompose(item1)), ulen(decompose(item2))
		
		if sort1 == sort2 then
			-- Sort ᾱ or ᾰ before α.
			if decomp_length1 > decomp_length2 then
				return true
			else
				return false
			end
		else
			return sort1 < sort2
		end
	end
	
	for key1, value1 in require('table').sortedPairs(detection_table, sort) do
		if key1:find '^longest' then
			out:insert('* ' .. key1:gsub('_', ' ') .. ': ' .. value1 .. ' characters')
		else
			table.insert(out, "\n* " .. labels[1] .. " " .. tag(key1))
			if type(value1) == "string" then
				out:insert(" &rarr; " .. tag(value1))
			elseif type(value1) == "table" then
				for key2, value2 in require('table').sortedPairs(value1, sort) do
					-- mw.log(len(key1), len(key2))
					out:insert("\n** " ..
							(noun and labels[2] or key2 == "ον" and "neuter" or "feminine") ..
							" " .. tag(key2) .. ": <code>" .. value2 .. "</code>")
					if noun then
						out:insert(" (<code>" .. (m_classes.conversion[value2] or "?") .. "</code>)")
					end
				end
			end
		end
	end
	
	return out:concat()
end
	

function export.show_noun_categories(frame)
	return print_detection_table(m_classes.infl_info.noun, { "nominative", "genitive" }, true)
end


function export.show_adj_categories(frame)
	return print_detection_table(m_classes.infl_info.adj, { "masculine", "feminine or neuter" })
end

return export