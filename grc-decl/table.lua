local path = 'Module:grc-decl'
local headers = mw.loadData(path .. '/decl/classes').headers

local str_find = string.find
local str_match = string.match
local str_gsub = string.gsub
local ustring_gsub = mw.ustring.gsub
local Array = require 'Module:array'

-- Commas or slashes in the cell for a particular form are converted to this.
local form_separator = ' / '

local export = {}

--[[
	Basic letters with and without diacritics, plus digamma and combining
	diacritics.
]]
local word_characters = require('grc-utilities.data').word_characters

-- displayed in cell that has no form in it
local empty_cell = '—'

local nonAttic_note = 'Dialects other than Attic are not well attested. ' ..
	'Some forms may be based on conjecture. Use with caution.'
local Attic_note = 'This table gives Attic inflectional endings. ' ..
	'For declension in other dialects, see [[Appendix:Ancient Greek dialectal declension]].'

local case_names = { 'Nominative', 'Genitive', 'Dative', 'Accusative', 'Vocative' }

local function form_is_empty(form)
	return not form or form == '' or form == '-' or form == '—'
end

-- Use the fields in a table to fill out template parameter syntax in a string.
local function fill_params(str, mapping)
	str = str:gsub('{{{([^}]+)}}}',
		function(key)
			return mapping[key] or error("Parameter " .. key .. " not found.")
		end)
	return str
end

local lang = require('languages').getByCode('grc')

local full_link = require('links').full_link
local function entry_link(term, accel)
	return full_link({ lang = lang, term = term, tr = '-', accel = accel }, nil, false)
end

-- Creates a callable table that saves previous transliterations.
-- Helpful because most paradigms have some syncretic forms; particularly useful for neuter forms.
local transliterate = require('fun').memoize(require('Module:grc-translit').tr)

local tag_translit = require('Module:script utilities').tag_translit
local function format_translit(Greek_text)
	return tag_translit(transliterate(Greek_text), lang, 'default')
end

local function get_label_display(dialect)
	return require('labels').get_label_info { label = dialect, lang = lang, nocat = true}.label
end

local function get_stylesheet()
	return require('TemplateStyles')("Module:grc-decl/style.css")
end

local function make_number_table(number_arg)
	local numbers = {}
	for _, number in ipairs{ { 'S', 'Singular' }, { 'D', 'Dual' }, { 'P', 'Plural' } } do
		if number_arg[number[1]] then
			table.insert(numbers, number[2])
		end
	end
	return numbers
end

local function link(alt, accel)
	if alt == '-' then
		return '-'
	end
	
	alt = str_gsub(alt, 'σ$', 'ς') --just in case
	if str_find(alt, '%b()') then
		local no_paren_content, with_paren_content =
				str_gsub(alt, '%b()', ''), str_gsub(alt, '[()]', '')
		
		-- This expands πᾶσῐ(ν) to πᾶσῐ / πᾶσῐν so that both terms can be found
		-- in searches.
		return entry_link(no_paren_content, accel) .. form_separator
			.. entry_link(with_paren_content, accel)
	else
		return entry_link(alt, accel)
	end
end

local function get_header(code, irregular, indeclinable)
	if not code then
		if irregular then
			return 'Irregular declension'
		elseif indeclinable then
			return 'Declension'
		else
			return "??"
		end
	elseif #code > 5 then
		mw.log('grc-decl/header not code')
		return code
	else
		return headers[code] or
			error('No header for the code ' .. code .. '.')
	end
end

-- Case abbreviations used by {{inflection of}}.
local inflection_of_case_abbreviations = {
	N = 'nom', G = 'gen', D = 'dat', A = 'acc', V = 'voc'
}

local function link_form(args, form_code, istitle)
	local form_table = args.adjective and args.atable or args.ctable
	local form = form_table[form_code]
	
	if form_is_empty(form) then return empty_cell end
	
	-- if it is a title form, strip all but the first variation
	if istitle then
		form = str_match(form, '[^,/]+') --capture up to comma or slash (needs standardization)
		form = ustring_gsub(form, '%s+$', '') --strip final whitespace
	else
		-- convert commas to slashes and space the slashes for legibility
		form = ustring_gsub(form, '%s*[/,]%s*', form_separator)
		form_table[form_code] = form
	end
	
	-- concat article
	if (not args.adjective) and args.article[form_code] and form_code:sub(1, 1) ~= 'V' then
		form = args.article[form_code] .. ' ' .. form
	end
	
	local accel_prefix
	if args.adjective then
		-- Generate acceleration information ([[WT:ACCEL]]) for declined forms
		-- and for the comparative and superlative forms.
		if form_code:find('^%u+$') then
			local gender, case, number = form_code:match('^(.)(.)(.)$')
			gender, number = gender:lower(), number:lower()
			case = inflection_of_case_abbreviations[case]
				or error("Case " .. case .. " not recognized.")
			
			-- If feminine nominative singular is absent, masculine and feminine
			-- are probably the same?
			local gender_codes = gender == 'm' and not args.atable.FNS and gender .. '//f'
				or gender
			accel_prefix = gender_codes .. '|' .. case .. '|' .. number
			
			if args.comparative then
				accel_prefix = accel_prefix .. '|comparative'
			elseif args.superlative then
				accel_prefix = accel_prefix .. '|superlative'
			end
		elseif form_code == "comp" then
			accel_prefix = 'comparative'
		elseif form_code == "super" then
			accel_prefix = 'superlative'
		end
	else
		local case, number = form_code:match('^(.)(.)$')
		number = number:lower()
		case = inflection_of_case_abbreviations[case]
			or error("Case '" .. tostring(case) .. "' not found.")
		accel_prefix = case .. '|' .. number
	end
		
	-- Add suffix, and make sure any macrons and breves are included in the
	-- non-lemma entry.
	local accel
	if accel_prefix then
		local origin
		if args.decl_type == "irreg" or args.decl_type == "indecl" then
			origin = args[2]
		else
			for _, number in ipairs { 'S', 'D', 'P' } do
				if args.number[number] then
					local code = 'N' .. number
					if args.adjective then
						code = 'M' .. code
					end
					origin = args[code] or form_table[code] or args[1]
					break
				end
			end
		end
		
		origin = origin or args[1] -- just in case
		
		accel = {form = accel_prefix, lemma = origin}
	end
	
	--[[
		An Ancient Greek word character optionally preceded by a hyphen or
		followed by a sequence of word characters or parentheses.
		Matches -ᾰ́ς, σοῖσι(ν), as well as cases with parentheses in the middle
		of the word.
	]]
	local linked_form = ustring_gsub(form,
		'%-?[' .. word_characters .. '][' .. word_characters .. '()]*',
		function (form)
			return link(form, accel)
		end)
	
	if istitle then
		return linked_form
	else
		return linked_form .. '<br/>' .. format_translit(form)
	end
end

local function make_title(args)
	local title = Array()
	title:insert(get_header(args.declheader, args.irregular, args.indeclinable) .. ' of ')
	
	-- Display the nominative and genitive form for the first number that has
	-- forms.
	for _, number_code in ipairs{ 'S', 'D', 'P' } do
		if args.number[number_code] then
			title:insert(link_form(args, 'N' .. number_code, true) .. '; '
				.. link_form(args, 'G' .. number_code, true))
			break
		end
	end
	
	if args.dial then
		table.insert(args.titleapp, get_label_display(args.dial))
	end
	
	if args.titleapp[1] then
		title:insert(' (' .. table.concat(args.titleapp, ', ') .. ')')
	end
	
	return title:concat()
end

local case_header =
[[
|-
! class="case-header" | {{{case_name}}}
]]
local form_cell =
[[
| class="form" data-accel-col="{{{col}}}" | {{{form}}}
]]
local function make_rows(args, nums)
	local rows = Array()
	
	if not args.adjective then
		case_header = case_header
		form_cell = form_cell
	end
	
	for _, case_name in ipairs(case_names) do
		rows:insert((case_header:gsub("{{{case_name}}}", case_name)))
		local case_abbr = case_name:sub(1, 1)
		for i, number in ipairs(nums) do
			rows:insert(fill_params(form_cell, {
				form = link_form(args, case_abbr .. number:sub(1, 1)),
				col = i,
			}))
		end
	end
	
	return rows:concat()
end

local notes_template =
[[
|-
! class="notes-header" | Notes:
| {{{extra_cell}}}class="notes" colspan="13" | <div class="use-with-mention">{{{notes}}}</div>
]]

local function make_notes(args)
	args.notes = Array(args.notes)
	
	if args.dial ~= 'koi' and args.dial ~= 'gkm' then
		args.notes:insert(1,
			args.dial ~= 'att' and nonAttic_note
			or Attic_note)
	end
	
	if args.user_notes then -- add user notes
		args.notes:insert(args.user_notes)
	end
	
	if args.debug then
		args.notes:insert(args.debug)
	end
	
	if next(args.notes) == nil then
		return ""
	end
	
	return fill_params(notes_template, {
		extra_cell = args.adjective and '\n| ' or '',
		notes = args.notes
			:map(function (note) return "\n* " .. note end):concat(),
	})
end

local number_header =
[[
! class="number-header" | {{{number}}}
]]

local noun_table_top =
[=[
<div class="NavFrame grc-decl">
<div class="NavHead">{{{title}}}</div>
<div class="NavContent">
{| class="inflection-table inflection-table-grc"
! class="case-number-header" | Case / #
]=]

function export.make_table(args)
	local nums = make_number_table(args.number)
	
	if not args.adjective then
		noun_table_top = noun_table_top
		number_header = number_header
	end
	
	-- This can be simplified.
	-- Percents have to be escaped (otherwise, strangely, a null character is
	-- inserted).
	local output = Array(
		(noun_table_top
			:gsub('{{{title}}}', make_title(args))))
	
	for _, number in ipairs(nums) do
		output:insert((number_header:gsub('{{{number}}}', number)))
	end
	output:insert(make_rows(args, nums))
	output:insert(make_notes(args))
	output:insert('|}</div></div>')
	if args.categories[1] and mw.title.getCurrentTitle().nsText == '' then
		output:insert(require('Module:utilities').format_categories(args.categories, lang))
	end
	
	return output:concat() .. get_stylesheet()
end

local function make_title_adj(args, genders)
	if args.title then
		return args.title
	else
		local title = Array()
		title:insert(get_header(args.adeclheader, args.irregular, args.indeclinable) .. ' of ')
		
		for _, number in ipairs{ 'S', 'D', 'P' } do
			if args.number[number] then
				local gender_forms = {}
				for _, gender in ipairs(genders) do
					table.insert(gender_forms, link_form(args, gender .. 'N' .. number, true))
				end
				title:insert(table.concat(gender_forms, '; '))
				break
			end
		end
		
		if args.dial then
			table.insert(args.titleapp, get_label_display(args.dial))
		end
		
		if args.titleapp[1] then
			title:insert(' (' .. table.concat(args.titleapp, ', ') .. ')')
		end
		
		return title:concat()
	end
end

local function make_rows_adj(args, nums, genders)
	local rows = Array()
	
	for _, case_name in ipairs(case_names) do
		rows:insert((case_header:gsub('{{{case_name}}}', case_name)))
		for i, number in ipairs(nums) do
			rows:insert('|\n')
			local case_number = case_name:sub(1, 1) .. number:sub(1, 1)
			for _, gender in ipairs(genders) do
				rows:insert(fill_params(form_cell, {
					form = link_form(args, gender .. case_number),
					col = i
				}))
			end
		end
	end
	return rows:concat()
end

-- Add the part of the table containing the adverb and the comparative and
-- superlative forms, if applicable.
local function make_acs_adj(args, nums)
	-- This should only apply to pronouns. I think.
	-- If all of adverb, comparative, and superlative are absent, don't display
	-- the "derived forms" part of the table at all.
	if #nums < 3 or require 'Module:fun'.all(
			function (form_code)
				return form_is_empty(args.atable[form_code])
			end,
			{ 'adv', 'comp', 'super' }) then
		return ''
	end
	
	args.atable.adv = args.atable.adv
	args.atable.comp = args.atable.comp
	args.atable.super = args.atable.super
	
	local fill = {
		colspan = (args.act and args.act[2] or args.irregular) and '3' or '2',
		adv = link_form(args, 'adv'),
		comp = link_form(args, 'comp'),
		super = link_form(args, 'super'),
	}
	
	local acs_section = [=[
|-
! class="derived-forms-header" rowspan="2" | Derived forms
|
! class="derived-form-name-header" colspan={{{colspan}}} | Adverb
|
! class="derived-form-name-header" colspan={{{colspan}}} | Comparative
|
! class="derived-form-name-header" colspan={{{colspan}}} | Superlative
|-
|
| class="form" colspan={{{colspan}}} | {{{adv}}}
|
| class="form" colspan={{{colspan}}} | {{{comp}}}
|
| class="form" colspan={{{colspan}}} | {{{super}}}
]=]
	
	return fill_params(acs_section, fill)
end

local adj_table_top =
[=[
<div class="NavFrame grc-decl grc-adecl">
<div class="NavHead">{{{title}}}</div>
<div class="NavContent">
{| class="inflection-table inflection-table-grc"
! class="number-header" | Number
]=]

function export.make_table_adj(args)
	local nums = make_number_table(args.number)
	
	local threept = not(args.act and args.act[2] == nil)
	local genders = threept and { 'M', 'F', 'N' } or { 'M', 'N' }
	local number_header =
[=[
! class="divider" |
! class="number-header" colspan=]=] .. (threept and '3' or '2') .. "| {{{number}}}\n"

	local gender_headers =
[=[
|
! class="gender-header" | Masculine]=] .. (threept and [=[
!! class="gender-header" | ]=] or [=[ / ]=]) .. [=[Feminine
!! class="gender-header" | Neuter
]=]

	local output = Array(
		(adj_table_top:gsub('{{{title}}}', make_title_adj(args, genders)))
	)
	for _, number in ipairs(nums) do
		output:insert((number_header:gsub('{{{number}}}', number)))
	end
	output:insert([=[|-
! class="case-gender-header" | Case/Gender
]=])
	for _, _ in ipairs(nums) do
		output:insert(gender_headers)
	end
	output:insert(make_rows_adj(args, nums, genders))
	output:insert(make_acs_adj(args, nums))
	output:insert(make_notes(args))
	output:insert('|}</div></div>')
	
	if args.categories[1] and mw.title.getCurrentTitle().nsText == '' then
		output:insert(require('Module:utilities').format_categories(args.categories, lang))
	end
	
	return output:concat() .. get_stylesheet()
end

return export