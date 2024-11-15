local export = {}

local module_path = "grc-decl.lua"

local m_grc_decl_table = require(module_path .. '/table')
local m_grc_decl_decl = require(module_path .. '/decl')
local m_params = mw.loadData(module_path .. "/params")

local m_table = require('table.lua')

local usub = mw.ustring.sub
local ufind = mw.ustring.find
local decompose = mw.ustring.toNFD

local shared = require('grc-decl.shared.lua')
local quote, track = shared.quote, shared.track

local function handle_unrecognized_args(unrecognized_args, adjective)
	-- Next returns nil if table is empty.
	if next(unrecognized_args) then
		local template_name = adjective and 'grc-adecl' or 'grc-decl'
		local track = track(template_name)
		track("unrecognized args")
		
		local unrecognized_list = m_table.keysToList(unrecognized_args)
		local agreement = #unrecognized_list > 1 and "s" or ""
		
		mw.addWarning("unrecognized argument" .. agreement .. " in " ..
				mw.text.nowiki("{{" .. template_name .. "}}") .. ": " .. 
				table.concat(unrecognized_list, ", ") ..
				"; see Module:grc-decl/params for a full list of recognized args")
	end
end

local function swap_args(args, suffix)
	--This function has undefined behavior if both <arg> and <arg><suffix> are
	--specified; use e.g. <arg>1 and <arg>2 instead.
	local args_ = args
	args = {}
	for code, value in pairs(args_) do
		if type(code) == 'number' then
			args[code] = value
		else
			-- Removes suffix from the end of string keys.
			args[code:gsub(suffix .. '$', '')] = value
		end
	end
end

local function interpret_form(form_param, is_adjective)
	if type(form_param) ~= 'string' then
		return {}, {}, nil, nil
	end
	
	local no_article = form_param:find('X') and true or false
	if no_article and is_adjective then
		error('Adjectives cannot have articles. Remove ' .. quote('X') ..
			' option in the ' .. quote('form') .. ' parameter.')
	end
	
	-- Convert sing, dual, plur to S, D, P.
	-- Remove other lowercase letters. This removes "con" and "open".
	local number_codes = { sing = true, dual = true, plur = true }
	local contracted, comparative
	local new_form = form_param:gsub('((%l)%l+)', function(wholematch, initial)
			if wholematch == 'con' then
				contracted = true
			elseif wholematch  == 'open' then
				contracted = false
			elseif wholematch == 'comp' then
				comparative = true
			elseif number_codes[wholematch] then
				return initial:upper()
			end
			return ''
		end)
	
	--[[
		Returns tables containing all genders and numbers.
		For instance, for nouns that are variably masculine or feminine:
			args.gender		{ "M", "F", ["M"] = true, ["F"] = true }
			args.number		{ "S", "D", "P", ["S"] = true, ["D"] = true, ["P"] = true }
		Not sure if the sequential entries are needed.
	]]
	
	-- Find contiguous gender abbreviations.
	local genders = new_form:match("[MFN]+")
	
	if is_adjective and genders then
		error("Adjectives cannot have gender specified in the form parameter.")
	end
	
	-- Find number abbreviations.
	-- If no number, assume all numbers will be displayed.
	local numbers = new_form:gsub('[^SDP]+', '')
	if numbers == '' then
		numbers = 'SDP'
	end
	
	if genders then
		genders = mw.text.split(genders, "")
		for i, gender in ipairs(genders) do
			if gender == "" then
				genders[i] = nil
			else
				genders[gender] = true
			end
		end
		if genders.N and ( genders.M or genders.F ) then
			error("A noun cannot be neuter and another gender at the same time.")
		end
	else
		genders = {}
	end
	if numbers then
		numbers = mw.text.split(numbers, "")
		for i, number in ipairs(numbers) do
			if number == "" then
				numbers[i] = nil
			else
				numbers[number] = true
			end
		end
		if numbers.S and numbers.D and numbers.P then
			numbers.F = true
		end
	else
		numbers = {}
	end
	
	return genders, numbers, no_article, contracted, comparative
end

-- Canonicalize specially-handled dialect codes.
local function handle_dialect(dialect)
	if dialect == "Homeric" then
		dialect = "hom"
	elseif dialect == "Attic" then
		dialect = "att"
	elseif dialect == "Epic" then
		dialect = "epi"
	elseif dialect == "Ionic" then
		dialect = "ion"
	end
	if dialect == "hom" then
		dialect = "epi"
	end
	return dialect
end

local function handle_unmarked_length(arg1, arg2, adjective)
	local old_arg1, old_arg2 = arg1, arg2
	if arg2 then
		local m_accent = require("grc-accent.lua")
		local standard_diacritics = require("grc-utilities.lua").standardDiacritics
		if arg1 == 'irreg' or arg1 == 'indecl' then
			arg2 = m_accent.mark_implied_length(standard_diacritics(arg2))
		else
			arg1, arg2 = m_accent.harmonize_length(standard_diacritics(arg1), standard_diacritics(arg2))
		end
	end
	
	local track = track(adjective and 'grc-adecl' or 'grc-decl')
	
	--[=[
	[[Special:WhatLinksHere/Wiktionary:Tracking/grc-decl/length marked on arg1]]
	[[Special:WhatLinksHere/Wiktionary:Tracking/grc-decl/length marked on arg2]]
	[[Special:WhatLinksHere/Wiktionary:Tracking/grc-adecl/length marked on arg1]]
	[[Special:WhatLinksHere/Wiktionary:Tracking/grc-adecl/length marked on arg2]]
	]=]
	if old_arg1 and arg1 ~= decompose(old_arg1) then
		track('length marked on arg1')
	end
	
	if old_arg2 and arg2 ~= decompose(old_arg2) then
		track('length marked on arg2')
	end
	
	return arg1, arg2
end

local function get_args(args, is_adjective, function_name)
	-- Have to process args[1] before 'irreg' or 'indecl' is checked for.
	local arg1 = mw.text.trim(args[1])
	if arg1 == '' then arg1 = nil end
	
	local irreg = arg1 == 'irreg'
	local indecl = arg1 == 'indecl'
	
	local form_param = args.form
	
	-- [[Special:WhatLinksHere/Wiktionary:Tracking/grc-adecl/empty comp or super]]
	if is_adjective then
		if args.deg then
			if not (args.deg == 'comp' or args.deg == 'super') then
				error('Adjective degree ' .. quote(args.deg) .. ' not recognized.')
			end
			
			-- Comparatives sometimes are treated as the lemma because there is
			-- no positive form. Superlatives should not be lemmas?
			if args.deg == 'comp' and args.comp
					or args.deg == 'super' and (args.super or args.comp) then
				local form_name = args.deg == 'comp' and 'comparative' or 'superlative'
				error(("A %s adjective cannot have a %s form specified.")
					:format(form_name, form_name))
			end
		end
	end
	
	local dialect_code
	local params = m_params[(irreg and 'irreg_' or '') ..
		(irreg and form_param and form_param:find('N') and 'N_' or '') ..
		(is_adjective and 'adj_' or 'noun_') ..
		'params']
	local args, unrecognized_args = require('parameters.lua').process(args, params, true, "grc-decl", function_name)
	
	handle_unrecognized_args(unrecognized_args, is_adjective)
	form_param, dialect_code = args.form, args.dial
	args.maxindex = m_table.length(params)
	
	if irreg then
		require('debug.lua').track('grc-decl/irreg')
	end
	
	if is_adjective then
		args.adjective = true
		args.atable = {}
		
		if args.hp then
			track('grc-adecl', 'hp')
		end
	end
	
	args[1], args[2] = handle_unmarked_length(args[1], args[2], is_adjective)
	local arg2 = args[2]
	args.dial = handle_dialect(dialect_code)
	args.gender, args.number, args.no_article, args.contracted, args.comparative =
		interpret_form(form_param, is_adjective)
	
	if args.comparative then
		if (arg2 or args.dial ~= 'att' or not arg1:find("ον$")) then
			error("|form=comp is only meant for Attic third-declension comparatives with a stem in " .. quote("-ον") .. ".")
		end
		
		if args.deg then
			error('|form=comp not needed when |deg=comp is set.')
		end
	end
	
	if args.deg == 'comp' then
		args.comparative = true
	elseif args.deg == 'super' then
		args.superlative = true
	end
	
	args.indeclinable, args.irregular = indecl, irreg
	
	args.categories = {}
	
	local track = track(is_adjective and 'grc-adecl' or 'grc-decl')
	
	if ((arg1 or '') .. (arg2 or '')):find('˘') then
		track('manual-breve')
	end
	
	if args.titleapp then
		track('titleapp')
	end
	
	for _, v in ipairs({ 'titleapp', 'titleapp1', 'titleapp2' }) do
		if args[v] then
			args[v] = mw.text.split(args[v], '%s*[/,]%s*')
		else
			args[v] = {}
		end
	end
	
	for _, v in ipairs({ 'notes', 'notes1', 'notes2' }) do
		if args[v] then
			args['user_' .. v] = args[v] --convert 'notes' to 'user_notes'
			args[v] = {}
		else
			args[v] = {}
		end
	end
	args.form_cache = {}
	
	return args
end

--[=[
-- This function is an entry point for testing noun functionality only
-- ]=]
function export.test_decl(frame)
	local args = get_args(frame, false, "test_decl")
	m_grc_decl_decl.get_decl(args)
	m_grc_decl_decl.make_decl(args, args.decl_type, args.root)
	return args
end

-- These conditions should be mutually exclusive so that we don't need two
-- separate functions.
local function uncontracted_condition(dialect, contracted)
	return dialect == 'ion' or dialect == 'epi'
		or not (contracted == true or dialect == 'att')
end

local function contracted_condition(dialect, contracted)
	return not (dialect == 'ion' or dialect == 'epi' or contracted == false)
end

function export.decl(frame)
	local args = get_args(frame:getParent().args, false, "decl")
	m_grc_decl_decl.get_decl(args)
	
	if args.root:sub(1, 1) == '-' and not args.form:find('[MFN]') then
		args.no_article = true
	end
	if args.decl_type:find('2nd') and not args.decl_type:find('N') and not args.form:find('[MFN]') then
		table.insert(args.categories, 'Ancient Greek second-declension nouns without gender specified')
	end
	
	if args.decl_type:find('κλῆς') or ufind(args.decl_type, '[ᾰε]σ') then
		local out = {}
		
		if uncontracted_condition(args.dial, args.contracted) then
			args.titleapp = {}
			swap_args(args, 1)
			table.insert(args.titleapp, 'uncontracted')
			m_grc_decl_decl.make_decl(args, args.decl_type, args.root)
			args.article = m_grc_decl_decl.infl_art(args)
			table.insert(out, m_grc_decl_table.make_table(args))
		end
		
		if contracted_condition(args.dial, args.contracted) then
			args.titleapp = {}
			swap_args(args, 2)
			table.insert(args.titleapp, '[[Appendix:Ancient Greek contraction|contracted]]')
			m_grc_decl_decl.make_decl(args, args.decl_type, args.root)
			args.article = m_grc_decl_decl.infl_art(args)
			
			table.insert(out, m_grc_decl_table.make_table(args))
		end
		return table.concat(out, '\n')
	else
		m_grc_decl_decl.make_decl(args, args.decl_type, args.root)
		args.article = m_grc_decl_decl.infl_art(args)
		return m_grc_decl_table.make_table(args)
	end
end

--[=[
-- This function is an entry point for testing adjective functionality only
-- ]=]
function export.test_adecl(frame)
	local args = get_args(frame, true, "test_adecl")
	m_grc_decl_decl.get_decl_adj(args)
	args.act = m_grc_decl_decl.adjinflections[args.decl_type]
	m_grc_decl_decl.make_decl_adj(args, m_grc_decl_decl.adjinflections[args.decl_type])
	return args
end

function export.adecl(frame)
	local args = get_args(frame:getParent().args, true, "adecl")
	m_grc_decl_decl.get_decl_adj(args)
	
	if m_grc_decl_decl.adjinflections_con[args.decl_type] then
		local out = {}
		
		if uncontracted_condition(args.dial, args.contracted) then
			args.titleapp, args.notes, args.categories = {}, {}, {}
			swap_args(args, 1)
			table.insert(args.titleapp, 'uncontracted')
			
			args.act = m_grc_decl_decl.adjinflections[args.decl_type]
			m_grc_decl_decl.make_decl_adj(args, m_grc_decl_decl.adjinflections[args.decl_type])
			table.insert(out, m_grc_decl_table.make_table_adj(args))
		end
		
		if contracted_condition(args.dial, args.contracted) then
			args.titleapp, args.notes, args.categories = {}, {}, {}
			swap_args(args, 2)
			
			table.insert(args.titleapp, '[[Appendix:Ancient Greek contraction|contracted]]')
			
			args.act = m_grc_decl_decl.adjinflections_con[args.decl_type]
			m_grc_decl_decl.make_decl_adj(args, m_grc_decl_decl.adjinflections_con[args.decl_type])
			table.insert(out, m_grc_decl_table.make_table_adj(args))
		end
		return table.concat(out, '\n')
	else
		args.act = m_grc_decl_decl.adjinflections[args.decl_type]
		m_grc_decl_decl.make_decl_adj(args, m_grc_decl_decl.adjinflections[args.decl_type])
		return m_grc_decl_table.make_table_adj(args)
	end
end


local function tag(text)
	local lang = require("languages.lua").getByCode("grc")
	return require("Module:script utilities").tag_text(text, lang)
end

function export.show_noun_forms(frame)
	local args = get_args(frame.args[1] and frame.args or frame:getParent().args, false, "show_noun_forms")
	m_grc_decl_decl.get_decl(args)
	
	local success, message = pcall(m_grc_decl_decl.make_decl, args, args.decl_type, args.root)
	
	if not success then
		return 'Declension generation failed for ' .. args[1] .. (args[2] and ', ' .. args[2] or '') .. ': ' ..
			message
	end
	
	-- mw.logObject(args)
	
	local inflections = args.ctable
	
	local cases = { "N", "A", "V", "G", "D" }
	local numbers = { "S", "D", "P" }
	
	local out = { "\n* " .. tag(args[1]) .. ", " .. tag(args[2]) }
	for _, number in ipairs(numbers) do
		table.insert(out, "\n** ")
		local number_forms = {}
		
		for _, case in ipairs(cases) do
			local code = case .. number
			local form = inflections[code]
			
			if form then
				table.insert(number_forms, tag(form))
			end
		end
		
		number_forms = table.concat(number_forms, ", ")
		
		table.insert(out, number_forms)
	end
	
	return table.concat(out)
end

function export.show_adj_forms(frame)
	local args = get_args(frame.args[1] and frame.args or frame:getParent().args, true, "show_adj_forms")
	m_grc_decl_decl.get_decl_adj(args)
	
	args.act = m_grc_decl_decl.adjinflections[args.decl_type]
	m_grc_decl_decl.make_decl_adj(args, m_grc_decl_decl.adjinflections[args.decl_type])
	
	-- mw.logObject(args)
	
	local function print(key, value)
		return key .. " = " .. "'" .. value .. "', "
	end
	
	local inflections = args.atable
	
	local genders = { "M", "F", "N" }
	local numbers = { "S", "D", "P" }
	local cases = { "N", "A", "V", "G", "D" }
	
	local out = {}
	
	table.insert(out, "{ '" .. args[1] .. "'")
	if args[2] then
		table.insert(out, ", '" .. args[2] .. "'")
	end
	table.insert(out, " },\n{")
	
	for _, gender in pairs(genders) do
		table.insert(out, "\n\t")
		for _, number in pairs(numbers) do
			for _, case in pairs(cases) do
				local code = gender .. case .. number
				local form = inflections[code]
				
				if form then
					table.insert(out, print(code, form))
				end
			end
		end
	end
	
	table.insert(out, "\n\t")
	
	local forms = { "adv", "comp", "super" }
	for _, form in pairs(forms) do
		if inflections[form] then
			table.insert(out, print(form, inflections[form]))
		end
	end
	
	table.insert(out, "\n},")
	
	return frame:extensionTag("source", table.concat(out), {lang = "lua"})
end

return export