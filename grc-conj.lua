local export = {}

local data = require('grc-conj.data')
local m_accent = require('grc-accent')
local m_links = require('links')
local lang = require('languages').getByCode('grc')
local list_to_set = require('table').listToSet

local word_character = '[*%-͂̆̄́̀̈̓̔͜ͅΐ-ώϘ-ϡἀ-ῼ]'

--[[
	Abbreviations:
- ctable, pctable: conjugation table, passive conjugation table
- pstem: passive stem
]]

local conjugations = {}

local args = {}
local tense, conjtype -- e.g. pres, pres-con-a respectively
local stem, stem1, stem2, stem3, stem4, pstem, pstem2 -- stem2 is for non-indicative (non-augmented) aorist
local ctable, pctable
local categories = ''

-- declarations of variables that would otherwise need to be global
local out, vowel, dialgroups, code, contractnote, stem
local makeconj, swapargs, dialform, dialforms_generic, dialforms_thematic,
	dialforms_thematic_passive, dialforms_contracted, dialforms_aorpass,
	make_table, get_title, link_form, link, make_num_header, make_rows,
	make_voice_header, make_nonfin_forms, make_notes


local contraction_symbols =
                    "Ê  Ē  É  Ĵ  Ĥ  Ḥ  Ô  Ō  Ó  Û   Ú   Ŵ  Ẃ  Î   Ī   Í"
-- These symbols correspond to the following vowels:
--                   ε  ε  έ  ει η  ῃ  ο  ο  ό  ου  ού  ω  ώ  οι  οι  οί
local contr = {
	['a']         = "ᾶ  ᾱ  ᾱ́  ᾷ  ᾶ  ᾷ  ῶ  ω  ώ  ῶ   ώ   ῶ  ώ  ῷ   ῳ   ῴ",
	['eta']       = "ῆ  η  ή  ῇ  ῆ  ῇ  ῶ  ω  ώ  ῶ   ώ   ῶ  ώ  ῷ   ῳ   ῴ",
	['e']         = "εῖ ει εί εῖ ῆ  ῇ  οῦ ου ού οῦ  ού  ῶ  ώ  οῖ  οι  οί",
	['o']         = "οῦ ου ού οῖ ῶ  οῖ οῦ ου ού οῦ  ού  ῶ  ώ  οῖ  οι  οί",
	['omega']     = "ῶ  ω  ώ  ῷ  ῶ  ῷ  ῶ  ω  ώ  ῶ   ῶ   ῶ  ώ  ῷ   ῳ   ῷ",
	['e-epiion']  = "εῖ ει εί εῖ ῆ  ῇ  εῦ ευ εύ εῦ  εύ  έω εώ έοι εοι εοί",
	['e-nonatt']  = "εῖ ει εί εῖ ῆ  ῇ  έο εο εό έου εού έω εώ έοι εοι εοί",
	['e-severe']  = "ῆ  η  ή  εῖ ῆ  ῇ  έο εο εό έου εού έω εώ έοι εοι εοί",
	['e-severe9'] = "ῆ  η  ή  εῖ ῆ  ῇ  ίο ιο ιό ίου ιού ίω ιώ ίοι ιοι ιοί",
	['e-boi']     = "εῖ ει εί εῖ εῖ εῖ ίο ιο ιό ίου ιού ίω ιώ ίοι ιοι ιοί",
	['e-mono']    = "εῖ εῖ εί εῖ έη έῃ έο εο εό έου εού έω εώ έοι εοι εοί",
}

-- Use metatable to generate a lookup table when contraction_types is indexed.
local contraction_types = setmetatable({}, {
	__index = function (contraction_types, code)
		local contraction_vowels = contr[code]
		if not contraction_vowels then
			return
		end
		
		local contraction_lookup = {}
		contraction_types[code] = contraction_lookup
		local get_next_contraction_symbol = mw.text.gsplit(contraction_symbols, "%s+")
		for contraction_result in mw.text.gsplit(contraction_vowels, "%s+") do
			contraction_lookup[get_next_contraction_symbol()] = contraction_result
		end
		return contraction_lookup
	end
})

local perf_euph = {
	{'μ[πβφ]', 'μμ','μψ','μπτ','μφθ'},
	{'γ[κγχ]', 'γμ','γξ','γκτ','γχθ'},
	{'[πβφ]',  'μμ','ψ', 'πτ', 'φθ'},
	{'[ζτδθσ]','σμ','σ', 'στ', 'σθ'}, -- θμ is retained in perfect mediopassive of κορύσσω.
	{'[κγχ]',  'γμ','ξ', 'κτ', 'χθ'},
	{'ν',      'σμ','νσ','ντ', 'νθ'}, -- TODO: this is also problematic because νμ > μμ sometimes
	{'λ',      'λμ','λσ','λτ', 'λθ'},
	{'ρ',      'ρμ','ρσ','ρτ', 'ρθ'},
	{'V',      'μ', 'σ', 'τ',  'σθ'},
}

local function get_label_display(dial)
	return require('labels').get_label_info { label = dial, lang = lang, nocat = true }.label
end

function export.show(frame)
	for k, v in pairs(frame:getParent().args) do
		args[k] = mw.text.trim(v)
	end
	
	-- check that the input is not malformed
	for i = 2, 5 do
		if args[i] then
			args[i] = mw.ustring.toNFD(args[i])
		end
	end
	
	if not args[1] or args[1] == '' then
		error('Parameter 1 (tense) is required. See [[Template:grc-conj/documentation]].')
	elseif not args[1]:find('irreg') then
		local malformed
		for i = 2, 5 do
			if args[i] and args[i] ~= m_accent.strip_tone(args[i]) then
				malformed = malformed or {}
				table.insert(malformed, i)
			end
		end
		if malformed then
			local plural = #malformed > 1
			error('Malformed input in parameter' .. (plural and 's ' or ' ') 
				.. require('table').serialCommaJoin(malformed) .. ' (contains extra accents)')
		end
	end
	
	conjtype = args[1]
	if conjtype == 'fut-ln' then conjtype = 'fut-con-e' end
	tense = conjtype:sub(1, (conjtype:find('-') or conjtype:len()+1)-1)
	stem1 = args[2] or ''
	stem2 = args[3] or '' -- augment or passive
	stem3 = args[4] or '' -- passive
	stem4 = args[5] or '' -- augmented passive
	
	if mw.ustring.find(stem1, '˘') then
		require('debug').track('grc-conj/manual-breve')
	end
	if args['dial1'] then require('debug').track('grc-conj/dial1') end
	if args['titleapp'] then require('debug').track('grc-conj/titleapp') end
	if args['prefix'] then
		require('debug').track('grc-conj/prefix')
		args['prefix'] = mw.ustring.toNFD(args['prefix'])
	end

	if args.form then
		local Array = require('array')
		local valid_words = Array {
			'con', 'open', 'act', 'mid', 'pass', 'am', 'ap', 'mp', 'full'
		}
		local invalid_words = Array(mw.text.split(args.form, '%A+'))
			:filter(function(word) return not valid_words:contains(word) end)
		if #invalid_words > 0 then
			error('Invalid words in |form= parameter: '
				.. invalid_words:concat ', ' .. '. Choose from '
				.. valid_words:concat ', ' .. '.')
		end
	else
		-- Determine which voices will be displayed based on the number of stems
		-- supplied and the tense.
		-- The argument is named 'form' for obsolete reasons.
		if tense == 'futp' then
			args.form = 'mp'
		elseif tense == 'fut' then
			if stem2 == '' then -- passive stem missing
				args.form = 'am'
			elseif stem1 == '' then -- active stem missing
				args.form = 'pass'
			end
		elseif tense == 'aor' then
			if stem3 == '' then -- passive indicative stem missing
				args.form = 'am'
			elseif stem1 == '' then -- active indicative stem missing
				args.form = 'pass'
			end
		elseif tense == 'perf' or tense == 'plup' then
			if stem2 == '' then -- passive stem missing
				args.form = 'act'
			elseif stem1 == '' then -- active stem missing
				args.form = 'mp'
			end
		end
		
		-- default
		if not args.form then
			args.form = 'full'
		end
	end

	if conjtype:match('con') then
		out = ''
		if conjtype:match('con%-[ae]$') and not args.form:match('con')
				and (args.dial == 'epi' or args.dial == 'ion' or args.dial == 'att'
					or not args.dial) then -- eta is too unpredictable
			swapargs(1)
			if args.dial then
				args.titleapp = args.titleapp or '(' .. get_label_display(args.dial) .. ', uncontracted)'
			else
				args.titleapp = args.titleapp1 or '(Uncontracted)'
			end
			vowel = conjtype:match('con%-(.*)')
			out = makeconj(tense, stem1 .. (conjtype:match('con%-a') and 'ᾰ' or 'ε'), stem2)
		end
		if not args.form:match('open') then
			swapargs(2)
			if args.dial then
				args.titleapp = args.titleapp2 or '(' .. get_label_display(args.dial) .. ', [[Appendix:Ancient Greek contraction|contracted]])'
			else
				args.titleapp = args.titleapp2 or '([[Appendix:Ancient Greek contraction|Contracted]])'
			end
			out = out .. makeconj(conjtype, stem1, stem2)
		end
		return out
	else
		return makeconj(conjtype, stem1, stem2)
	end
end

local function check_conjtype(conjtype)
	if not conjugations[conjtype] then
		local tense_names = {
			aor = 'aorist', imperf = 'imperfect', pres = 'present',
			fut = 'future', perf = 'perfect', plup = 'pluperfect',
			futp = 'future perfect',
		}
		local tense_code = conjtype:match '^%l+'
		if tense_code then
			if tense_names[tense_code] then
				local valid_conjugations_for_tense = require('array')
					.keys(conjugations)
					:filter(
						function (conjugation)
							return conjugation:match '^%l+' == tense_code
						end)
					:sort()
					:concat ', '
				error('No such conjugation for ' .. tense_code
					.. ' (' .. tense_names[tense_code]
					.. ' tense); choose between '
					.. valid_conjugations_for_tense .. '.')
			else
				error('No such tense: ' .. tense_code .. '; choose between '
					.. require('array').keys(tense_names)
						:map(
							function (tense_code)
								return tense_code .. ' (' .. tense_names[tense_code] .. ')'
							end)
						:concat ', '
					.. ', optionally with a suffix (see [[Template:grc-conj/documentation]] for a full list).')
			end
		else
			if not conjtype:find '^%l[%l%d-]+%l$' then
				error('Invalid characters in inflection: ' .. conjtype)
			else
				error('No such inflection: ' .. conjtype)
			end
		end
	end
end

function makeconj(conjtype, root, root2)
	check_conjtype(conjtype)
	stem = root
	stem2 = root2
	conjugations[conjtype]()
	return make_table()
end

function swapargs(suffix)
	--swaps the args so that functions returning multiple tables can have any form customized
	--This function has undefined behaviour if both <arg> and <arg><suffix> are
	--specified; use e.g. <arg>1 and <arg>2 instead.
	local args_ = args
	args = {}
	for code, value in pairs(args_) do
		args[mw.ustring.gsub(code, '(.+)' .. suffix .. '$', '%1')] = value
	end
end

local person_number_table = {'1S', '2S', '3S', '2D', '3D', '1P', '2P', '3P'}
local function iter_person_number()
	local iter, person_number_table, i = ipairs(person_number_table)
	local person_number
	return function ()
		i, person_number = iter(person_number_table, i)
		return person_number
	end
end

dialgroups = {
	['ark'] = list_to_set{'ara', 'kyp', 'ark'},
	['severe'] = list_to_set{'ara', 'kyp', 'ark', 'ele', 'lak', 'her', 'kre', 'les'}, -- lesbian was omitted from §25 — by mistake?
	['buck9'] = list_to_set{'boi', 'kyp',	'lak', 'her', 'kre'},
	['northwest'] = list_to_set{'pho', 'del', 'lok', 'ele'},
	['doric'] = list_to_set{'lak', 'her', 'meg', 'krn', 'kor', 'arg', 'rho', 'pam', 'koa', 'thr', 'kre', 'dor'},
	['west'] = list_to_set{'pho', 'del', 'lok', 'ele',
				'lak', 'her', 'meg', 'krn', 'kor', 'arg', 'rho', 'pam', 'koa', 'thr', 'kre', 'dor'},
	['nonIA'] = list_to_set{'ara', 'kyp', 'ark',
				 'les', 'the', 'boi',
				 'pho', 'del', 'lok', 'ele',
				 'lak', 'her', 'meg', 'krn', 'kor', 'arg', 'rho', 'pam', 'koa', 'thr', 'kre', 'dor'},
}

-- Koine is basically the same as Attic, right?
local function not_attic(dialect)
	return dialect and not (dialect == 'att' or dialect == 'koi')
end

function dialform(form_code, suffix, dialect, dialect2)
	if args.dial and (args.dial == dialect or 
					args.dial == dialect2 or 
					(dialgroups[dialect] and dialgroups[dialect][args.dial] ) ) then
		local forms = (form_code:sub(1, 1) == 'P') and pctable or ctable
		forms[form_code] = suffix
	end
end

function dialforms_generic(form_code, word)
	if not not_attic(args.dial) then
		return word
	end
	
	-- Epic forms (not in Buck)
	if args.dial == 'epi' and word then
		word = mw.ustring.gsub(word, 'μεθᾰ$', 'με(σ)θᾰ')
		
		-- possibly also in passive aorist (not attested)
		if form_code:match('AS1S') then
			word = word .. ', ' .. word .. 'μῐ'
		elseif form_code:match('AS2S') then
			word = word .. ', ' .. mw.ustring.gsub(word, 'ς$', 'σθᾰ')
		elseif form_code:match('AS3S') then
			word = word .. ', ' .. word .. 'σῐ'
		end
	end
	
	-- 102
	if dialgroups['nonIA'][args.dial] then
		word = mw.ustring.gsub(word, 'σῐ(ν)', 'σῐ')
	end
	
	-- 138.1 - data unclear
	
	-- 138.2
	if form_code:match('..3S') and dialgroups['west'][args.dial] then
		word = mw.ustring.gsub(word, 'σῐ', 'τῐ')
	end
	
	-- 138.3
	if form_code:match('..1P') and dialgroups['west'][args.dial] then
		word = mw.ustring.gsub(word, 'μεν$', 'μες')
	end
	
	-- 138.4 - can't be automated
	if args.dial == 'boi' or args.dial == 'the' then
		-- this is really 139.2 but it's easier to put here
		word = mw.ustring.gsub(word, 'νται$', 'νθαι')
		word = mw.ustring.gsub(word, 'ντο$', 'νθο')
	end
	
	-- 138.5 - can't be automated

	-- 138.6 (or 8)
	if dialgroups['nonIA'][args.dial] then
		word = mw.ustring.gsub(word, 'την$', 'τᾱν')
		word = mw.ustring.gsub(word, 'μην$', 'μᾱν')
		word = mw.ustring.gsub(word, 'σθην$', 'σθᾱν')
		word = mw.ustring.gsub(word, 'μένη$', 'μένᾱ')

		word = mw.ustring.gsub(word, 'Mην$', 'Mᾱν')
		word = mw.ustring.gsub(word, 'Hν$', 'Hᾱν')
		word = mw.ustring.gsub(word, 'Mένη$', 'Mένᾱ')
	end
	
	-- 139.1
	if args.dial == 'boi' then
		word = mw.ustring.gsub(word, 'αι$', 'η')
		word = mw.ustring.gsub(word, 'αι,', 'η,')
--	elseif args.dial == 'the' then -- this only happened at Larissa
--		word = mw.ustring.gsub(word, 'αι$', 'ει')
--		word = mw.ustring.gsub(word, 'αι,', 'ει,')
	elseif args.dial == 'ara' and form_code:match('[MP][IS]..') then
		word = mw.ustring.gsub(word, 'αι$', 'οι')
		word = mw.ustring.gsub(word, 'αι,', 'οι,')
	end
	if dialgroups['ark'][args.dial] then
		word = mw.ustring.gsub(word, 'ο$', 'υ')
	end
	
	-- 139.2
	if form_code:match('[MP]O3P') and (args.dial == 'ion' or args.dial == 'epi') then
		word = mw.ustring.gsub(word, 'ντο$', 'ᾰτο')
		-- This change adds a syllable.
		-- Fix accent: ἀγγελθησοίᾰτο, not ἀγγελθήσοιᾰτο.
		word = m_accent.antepenult(m_accent.strip_tone(word))
	end
	-- ion athematic -ᾰτ-: can't be automated
	-- boi -ᾰτ-: data unclear?
	-- boi/the -θ-: see under 138.4.
	
	-- 140
	if form_code == 'AC3P' then
		if dialgroups['ark'][args.dial] or (dialgroups['doric'][args.dial] and args.dial ~= 'kre') then
			word = mw.ustring.gsub(word, 'ντων$', 'ντω')
		elseif args.dial == 'boi' then
			word = mw.ustring.gsub(word, 'ντων$', 'νθω')
		elseif args.dial == 'les' or args.dial == 'pam' then
			word = mw.ustring.gsub(word, 'ντων$', 'ντον')
		elseif args.dial == 'late' then
			word = mw.ustring.gsub(word, 'ντων$', 'ντωσᾰν')
		end
	elseif form_code == 'MC3P' then
		if args.dial == 'kor' or args.dial == 'koa' then
			word = mw.ustring.gsub(word, 'ων$', 'ω')
		elseif args.dial == 'epd' or args.dial == 'lak' then
			-- thematic -οσθω for -εσθων must be dealt with separately. this also apples to ato and ele
			word = mw.ustring.gsub(word, 'ων$', 'ω')
		--not going to bother with corcyrian
		elseif args.dial == 'les' or args.dial == 'pam' then
			word = mw.ustring.gsub(word, 'ων$', 'ον')
		elseif args.dial == 'late' then
			word = mw.ustring.gsub(word, 'ων$', 'ωσᾰν')
		end
		
	end
	
	-- 151: data unclear
	
	-- 154: has to be done manually, as Attic has -ναι and -εναι; also Lesbian -ν and -μεναι
	
	-- 160: data unclear
	
	-- 221: I think it's probably best to fix things at around 400 BC, so CιV and ι=ει, η=αι, ει=η but υ=υ, οι=οι.
	
	-- 60.1
	if args.dial == 'ele' then
		word = mw.ustring.gsub(word, 'ς', 'ρ')
	end
	
	-- 66
	if args.dial == 'pam' then
		word = mw.ustring.gsub(word, 'νται$', 'δαι')
		word = mw.ustring.gsub(word, 'ντο$', 'δο')
		word = mw.ustring.gsub(word, 'ντι$', 'δι')
	end
	
	return word
end

function dialforms_thematic()
	dialform('AO2S', 'οισ(θᾰ)', 'epi')
	if conjtype:match('con') then
		--τιμα(ε)μεν(αι) is not apparently attested
	elseif m_accent.circ(stem) ~= m_accent.ult(stem) then
		--verb ends in a long vowel
		dialform('AI', 'ειν/έμεν(αι)/μεναι', 'epi')
	elseif m_accent.ult(stem) ~= stem then
		--verb ends in a [short] vowel
		dialform('AI', 'ειν/έμεν(αι)/μεν(αι)', 'epi')
	else
		dialform('AI', 'ειν/έμεν(αι)', 'epi')
	end

	if not_attic(args.dial) then
		ctable['MI2S'] = 'εαι'
		ctable['MS2S'] = 'ηαι'
		ctable['MC2S'] = 'εο'
	end
	
	dialform('MC2S', 'ιο', 'buck9') -- 9

	dialform('AS2D', 'ειτον', 'boi', 'the') -- 14
	dialform('AS3D', 'ειτον', 'boi', 'the')
	dialform('AS2P', 'ειτε', 'boi', 'the')
	dialform('MS2S', 'είαι', 'boi', 'the')
	dialform('MS3S', 'είται', 'boi', 'the')
	dialform('MS2D', 'εισθον', 'boi', 'the')
	dialform('MS3D', 'εισθον', 'boi', 'the')
	dialform('MS2P', 'εισθε', 'boi', 'the')

	dialform('AI2S', 'ῑς', 'boi') -- 28
	dialform('AI3S', 'ῑ', 'boi')
	dialform('AS2S', 'ῑς', 'boi') -- this is a conjecture
	dialform('AS3S', 'ῑ', 'boi')
	
	dialform('MC2S', 'ευ', 'ion') -- 42.5
	
	dialform('APF', 'ῶσᾰ', 'severe', 'boi') -- 77.3
	dialform('APF', 'όνσᾰ', 'kre', 'arg')
	dialform('APF', 'όνσᾰ', 'the', 'ark')
	dialform('APF', 'οισᾰ', 'les')
	
	dialform('AI3P', 'οντῐ', 'west') -- 138.4
	dialform('AS3P', 'ωντῐ', 'west')
	dialform('AI3P', 'ονσῐ', 'ara')
	dialform('AS3P', 'ωνσῐ', 'ara')
	dialform('AI3P', 'ωσῐ', 'kyp')
	dialform('AS3P', 'ωσῐ', 'kyp')
	dialform('AI3P', 'ονθῐ', 'boi', 'the')
	dialform('AS3P', 'ωνθῐ', 'boi', 'the')
	dialform('AI3P', 'οισῐ', 'les')
	dialform('AS3P', 'ῳσῐ', 'les')

	dialform('MC3P', 'όσθω', 'epd', 'lak') -- 140
	dialform('MC3P', 'ούσθω', 'kor')
	dialform('MC3P', 'όσθων', 'ato', 'ele')
	
	dialform('AS3S', 'η', 'ark') -- 149

	dialform('AI', 'ην', 'les') -- 153
	dialform('AI', 'εν', 'ark', 'del')
	dialform('AI', 'εν', 'doric')
	dialform('AI', 'ειν', 'krn', 'rho') -- exceptions to doric -εν
	dialform('AI', 'ην', 'ele', 'lak')
	dialform('AI', 'έμεν', 'boi', 'the') -- 155
end

function dialforms_thematic_passive()
	if not_attic(args.dial) then
		ctable['PI2S'] = 'ησεαι'
		ctable['PS2S'] = 'ησηαι'
		ctable['PC2S'] = 'ησεο'
	end
	
	dialform('PC2S', 'ησιο', 'buck9') -- 9

	dialform('PS2S', 'είαι', 'boi', 'the') -- 14
	dialform('PS3S', 'είται', 'boi', 'the')
	dialform('PS2D', 'εισθον', 'boi', 'the')
	dialform('PS3D', 'εισθον', 'boi', 'the')
	dialform('PS2P', 'εισθε', 'boi', 'the')

	dialform('PC2S', 'ευ', 'ion') -- 42.5
	
	dialform('PC3P', 'όσθω', 'epd', 'lak') -- 140
	dialform('PC3P', 'ούσθω', 'kor')
	dialform('PC3P', 'όσθων', 'ato', 'ele')
end


conjugations['pres'] = function()
	ctable = data.pres
	dialforms_thematic()
end

conjugations['imperf'] = function()
	ctable = data.imperf
end

function dialforms_contracted()
	if not_attic(args.dial) then
		-- ctable['MI2S'] = 'Êαι'
		-- ctable['MS2S'] = 'Ĥαι'
		-- ctable['MC2S'] = 'Êο'
		
		ctable['AO1S'] = 'Îμι'
		ctable['AO2S'] = 'Îς'
		ctable['AO3S'] = 'Î'
		ctable['AO2D'] = 'Îτον'
		ctable['AO3D'] = 'Íτην'
		ctable['AO1P'] = 'Îμεν'
		ctable['AO2P'] = 'Îτε'
		ctable['AO3P'] = 'Îεν'
	end

	dialform('APF', 'Ŵσᾰ', 'severe') -- 77.3
	dialform('APF', 'Ôνσᾰ', 'kre', 'arg')
	dialform('APF', 'Ôνσᾰ', 'the', 'ark')
--	dialform('APF', 'Îσᾰ', 'les')
	
	dialform('AI3P', 'Ôντῐ', 'west') -- 138.4
	dialform('AS3P', 'Ŵντῐ', 'west')
	dialform('AI3P', 'Ôνσῐ', 'ara')
	dialform('AS3P', 'Ŵνσῐ', 'ara')
	dialform('AI3P', 'Ŵσῐ', 'kyp')
	dialform('AS3P', 'Ŵσῐ', 'kyp')
	dialform('AI3P', 'Ôνθῐ', 'boi', 'the')
	dialform('AS3P', 'Ŵνθῐ', 'boi', 'the')
--	dialform('AI3P', 'Îσῐ', 'les')
--	dialform('AS3P', 'Yσῐ', 'les')
	
	dialform('MC3P', 'Óσθω', 'epd', 'lak') -- 140
	dialform('MC3P', 'Úσθω', 'kor')
	dialform('MC3P', 'Óσθων', 'ato', 'ele')
	
	dialform('AS3S', 'Ĥ', 'ark') -- 149

	dialform('AI', 'Éμεν', 'boi', 'the') -- 155
end

conjugations['pres-con-a'] = function()
	ctable = data.pres_contr
	
	dialform('AI', 'ᾶν/ήμεναι', 'epi')

	dialforms_contracted()
end

conjugations['imperf-con-a'] = function()
	ctable = data.imperf_contr
end

conjugations['pres-con-e'] = function()
	--The 'two-syllable' rule in Smyth 397 does not seem to be consistent
	--(does η/ηι/οι count?), and it's unclear to what degree it applied to
	--other dialects.
	ctable = data.pres_contr
	
	if not_attic(args.dial) then
	else
		ctable['MI2S'] = 'Ĵ, Ḥ'
	end
	
	dialform('AI', 'εῖν/ήμεναι/ῆναι', 'epi')
	dialform('MI2S', 'εῖαι/έαι', 'epi')
	dialform('MC2S', 'εῦ', 'epi')

	dialforms_contracted()
	
	dialform('MPM', 'είμενος', 'northwest', 'boi')
	dialform('MPF', 'ειμένᾱ', 'northwest', 'boi')
	dialform('MPN', 'είμενον', 'northwest', 'boi')
end

conjugations['imperf-con-e'] = function()
	ctable = data.imperf_contr

	dialform('MI2S', 'εῖο/έο', 'epi')
end

conjugations['pres-con-e-mono'] = function()
	ctable = data.pres_contr

	dialforms_contracted()
end

conjugations['imperf-con-e-mono'] = function()
	ctable = data.imperf_contr
end

conjugations['pres-con-o'] = function()
	ctable = data.pres_contr

	dialforms_contracted()
end

conjugations['imperf-con-o'] = function()
	ctable = data.imperf_contr
end

conjugations['pres-con-eta'] = function()
	ctable = data.pres_contr
end

conjugations['imperf-con-eta'] = function()
	ctable = data.imperf_contr
end

conjugations['pres-con-omega'] = function()
	ctable = data.pres_contr
end

conjugations['imperf-con-omega'] = function()
	ctable = data.imperf_contr
end

conjugations['pres-irreg'] = function()
	ctable = {}
	-- no pres-irregs have passive forms so we should be fine
	local i = 2
	for _, mood in ipairs({'I', 'S', 'O', 'C'}) do
		for person_number in iter_person_number() do
			args['A' .. mood .. person_number] = args['A' .. mood .. person_number] or args[i]
			i = i + 1
		end
	end
	args['AI'] = args['AI'] or args[34]
	args['APM'] = args['APM'] or args[35]
	args['APF'] = args['APF'] or args[36]
	args['APN'] = args['APN'] or args[37]
end

conjugations['imperf-irreg'] = function()
	ctable = {}
	local i = 2
	for person_number in iter_person_number() do
		args['AI' .. person_number] = args['AI' .. person_number] or args[i]
		i = i + 1
	end
end

conjugations['pres-ami'] = function()
	ctable = data.pres_ami
	
	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'αῖτον'
		ctable['AO3D'] = 'αίτην'
		ctable['AO1P'] = 'αῖμεν'
		ctable['AO2P'] = 'αῖτε'
		ctable['AO3P'] = 'αῖεν'
	end
	
	dialform('AC2S', 'η†/ᾰ', 'epi') --the AC2S is unclear but η is contracted from αε
	dialform('AI', 'ᾰ́μεν(αι)', 'epi')
	
	-- subjunctive seems to surprisingly end up just as Attic

	dialform('APM', 'αις', 'les') -- 77.3
	dialform('APF', 'αισᾰ', 'les')
	dialform('APF', 'ᾰ́νσᾰ', 'kre', 'arg')
	dialform('APF', 'ᾰ́νσᾰ', 'the', 'ark')
	
	dialform('AI3P', 'ᾰντῐ', 'west') -- 138.4
	dialform('AS3P', 'ῶντῐ', 'west')
	dialform('AI3P', 'ᾰνσῐ', 'ara')
	dialform('AS3P', 'ῶνσῐ', 'ara')
	dialform('AI3P', 'ᾱσῐ', 'kyp')
	dialform('AS3P', 'ῶσῐ', 'kyp')
	dialform('AI3P', 'ᾰνθῐ', 'boi', 'the')
	dialform('AS3P', 'ῶνθῐ', 'boi', 'the')
	dialform('AI3P', 'αισῐ', 'les')
	dialform('AS3P', 'ῷσῐ', 'les')

	dialform('AI1S', 'ᾱμῐ', 'nonIA') -- 138.6
	dialform('AI2S', 'ᾱς', 'nonIA') -- also -θα?
	dialform('AI3S', 'ᾱσῐ', 'nonIA')
	
	dialform('AI', 'ᾱν', 'les') -- 154, 155.3
	dialform('AI', 'ᾰ́μεν', 'the', 'boi')
	dialform('AI', 'ᾰ́μεν', 'west')
	dialform('AI', 'ᾰ́μην, ᾰ́μεν', 'kre')
	dialform('AI', 'ᾰ́μειν', 'rho')

	dialform('AC2S', 'ᾱ', 'nonIA') -- 160 - apparently smyth says that aeolic has ᾱ
end

conjugations['imperf-ami'] = function()
	ctable = data.imperf_ami
	
	dialform('AI3P', 'ᾰν', 'nonIA') -- 138.5
	
	dialform('AI1S', 'ᾱν', 'nonIA') -- 138.6
	dialform('AI2S', 'ᾱς', 'nonIA')
	dialform('AI3S', 'ᾱ', 'nonIA')
end

conjugations['pres-emi'] = function()
	ctable = data.pres_emi

	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'εῖτον'
		ctable['AO3D'] = 'είτην'
		ctable['AO1P'] = 'εῖμεν'
		ctable['AO2P'] = 'εῖτε'
		ctable['AO3P'] = 'εῖεν'
	end
	
	dialform('AS1S', 'εω', 'nonIA')
	dialform('AS2S', 'ηαι', 'nonIA')
	dialform('AS1P', 'εωμεν', 'nonIA')
	dialform('MS1S', 'εωμαι', 'nonIA')
	dialform('MS1P', 'εωμεν', 'nonIA')
	dialform('MS3P', 'εωνται', 'nonIA')
	
	dialform('AS1S', 'ιω', 'buck9')
	dialform('AS1P', 'ιωμεν', 'buck9')
	dialform('MS1S', 'ιωμαι', 'buck9')
	dialform('MS1P', 'ιωμεν', 'buck9')
	dialform('MS3P', 'ιωνται', 'buck9')

	dialform('MO3S', 'εῖτο', 'nonIA')
	dialform('MO2D', 'εῖσθον', 'nonIA')
	dialform('MO3D', 'είσθην', 'nonIA')
	dialform('MO1P', 'είμεθᾰ', 'nonIA')
	dialform('MO2P', 'εῖσθε', 'nonIA')
	dialform('MO3P', 'εῖντο', 'nonIA')
	
	dialform('AI2S', 'ης/ησθᾰ', 'epi')
	dialform('AI3S', 'ησῐ/εῖ', 'epi')
	dialform('AI3P', 'εῖσῐ', 'epi')
	dialform('AI', 'έμεν(αι)', 'epi')
	
	dialform('APF', 'ῆσᾰ', 'severe') -- 77.3
	dialform('APF', 'ένσᾰ', 'kre', 'arg')
	dialform('APF', 'ένσᾰ', 'the', 'ark')

	dialform('AI3P', 'εντῐ', 'west') -- 138.4
	dialform('AS3P', 'εωντῐ', 'west')
	dialform('AI3P', 'ενσῐ', 'ara')
	dialform('AS3P', 'εωνσῐ', 'ara')
	dialform('AI3P', 'ησῐ', 'kyp')
	dialform('AS3P', 'ιωσῐ', 'kyp')
	dialform('AI3P', 'ενθῐ', 'boi', 'the')
	dialform('AS3P', 'ιωνθῐ', 'boi')
	dialform('AS3P', 'εωνθῐ', 'the')
	dialform('AI3P', 'εισῐ', 'les')
	dialform('AS3P', 'εῳσῐ', 'les')
	
	dialform('AI', 'ην', 'les') -- 154, 155.3
	dialform('AI', 'έμεν', 'the', 'boi')
	dialform('AI', 'έμεν', 'west')
	dialform('AI', 'έμην, έμεν', 'kre')
	dialform('AI', 'έμειν', 'rho')
end

conjugations['imperf-emi'] = function()
	ctable = data.imperf_emi
	
	dialform('AI3P', 'εν', 'nonIA') -- 138.5
	dialform('AI3P', 'εᾰν', 'boi', 'kyp')

	dialform('AI1S', 'ην', 'nonIA') -- 160
	dialform('AI2S', 'ης', 'nonIA')
	dialform('AI3S', 'η', 'nonIA')
end

conjugations['pres-omi'] = function()
	ctable = data.pres_omi
	
	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'οῖτον'
		ctable['AO3D'] = 'οίτην'
		ctable['AO1P'] = 'οῖμεν'
		ctable['AO2P'] = 'οῖτε'
		ctable['AO3P'] = 'οῖεν'
	end
	
	dialform('AI2S', 'οῖσ(θᾰ)', 'epi')
	dialform('AI3S', 'ωσῐ/οῖ', 'epi')
	dialform('AI3P', 'οῦσῐ', 'epi')
	dialform('AI', 'όμεν(αι)', 'epi')

	dialform('APF', 'ῶσᾰ', 'severe', 'boi') -- 77.3
	dialform('APF', 'όνσᾰ', 'kre', 'arg')
	dialform('APF', 'όνσᾰ', 'the', 'ark')
	dialform('APM', 'οις', 'les')
	dialform('APF', 'οισᾰ', 'les')
	
	dialform('AI3P', 'οντῐ', 'west') -- 138.4
	dialform('AS3P', 'ῶντῐ', 'west')
	dialform('AI3P', 'ονσῐ', 'ara')
	dialform('AS3P', 'ῶνσῐ', 'ara')
	dialform('AI3P', 'ωσῐ', 'kyp')
	dialform('AS3P', 'ῶσῐ', 'kyp')
	dialform('AI3P', 'ονθῐ', 'boi', 'the')
	dialform('AS3P', 'ῶνθῐ', 'boi', 'the')
	dialform('AI3P', 'οισῐ', 'les')
	dialform('AS3P', 'ῳσῐ', 'les')

	dialform('AI', 'ων', 'les') -- 154, 155.3
	dialform('AI', 'όμεν', 'the', 'boi')
	dialform('AI', 'όμεν', 'west')
	dialform('AI', 'όμην, όμεν', 'kre')
	dialform('AI', 'όμειν', 'rho')

--	dialform('AI2S', 'οις', 'les') -- also -θα?
end

conjugations['imperf-omi'] = function()
	ctable = data.imperf_omi
	
	dialform('AI3P', 'ον', 'nonIA') -- 138.5
	dialform('AI3P', 'οᾰν', 'boi', 'kyp')

	dialform('AI1S', 'ων', 'nonIA') -- 160
	dialform('AI2S', 'ως', 'nonIA')
	dialform('AI3S', 'ω', 'nonIA')
end

conjugations['pres-numi'] = function()
	ctable = data.pres_numi
	
	dialform('APF', 'νυισᾰ', 'les') -- 77.3
	dialform('APF', 'νῠ́νσᾰ', 'kre', 'arg')
	dialform('APF', 'νῠ́νσᾰ', 'the', 'ark')
	
	dialform('AI3P', 'νῠντῐ', 'west') -- 138.4
	dialform('AS3P', 'νῠωντῐ', 'west')
	dialform('AI3P', 'νῠνσῐ', 'ara')
	dialform('AS3P', 'νῠωνσῐ', 'ara')
	dialform('AI3P', 'νῡσῐ', 'kyp')
	dialform('AS3P', 'νῠωσῐ', 'kyp')
	dialform('AI3P', 'νῠνθῐ', 'boi', 'the')
	dialform('AS3P', 'νῠωνθῐ', 'boi', 'the')
	dialform('AI3P', 'νυισῐ', 'les')
	dialform('AS3P', 'νῠῳσῐ', 'les')

	dialform('AI', 'νῡν', 'les') -- 154, 155.3
	dialform('AI', 'νῠ́μεν', 'the', 'boi')
	dialform('AI', 'νῠ́μεν', 'west')
	dialform('AI', 'νῠ́μην, νῠ́μεν', 'kre')
	dialform('AI', 'νῠ́μειν', 'rho')
end

conjugations['imperf-numi'] = function()
	ctable = data.imperf_numi
	
	dialform('AI3P', 'νῠν', 'nonIA') -- 138.5
	dialform('AI3P', 'νῠᾰν', 'boi', 'kyp')
end

conjugations['fut'] = function()
	ctable = data.pres
	pctable = data.fut_pass
	pstem = stem2
	dialforms_thematic()
	dialforms_thematic_passive()
end

conjugations['fut-con-a'] = function()
	ctable = data.pres_contr
	pctable = data.fut_pass
	pstem = stem2
	
	dialforms_contracted()

	dialform('AI', 'ᾶν/ήμεναι', 'epi')
end

conjugations['fut-con-e'] = function()
	ctable = data.pres_contr
	pctable = data.fut_pass
	pstem = stem2
	
	dialforms_contracted()

	dialform('AI', 'εῖν/ήμεναι/ῆναι', 'epi')
	dialform('MI2S', 'εῖαι/έαι', 'epi')
	dialform('MC2S', 'εῦ', 'epi')

	dialform('MPM', 'είμενος', 'northwest', 'boi')
	dialform('MPF', 'ειμένᾱ', 'northwest', 'boi')
	dialform('MPN', 'είμενον', 'northwest', 'boi')
end

conjugations['futp'] = function()
	ctable = data.pres
	dialforms_thematic()
end

function dialforms_aorpass()
	if mw.ustring.sub(pstem, -1) == 'θ' then
		pctable['PC2S'] = 'ητῐ'
	end

	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'εῖτον'
		ctable['AO3D'] = 'είτην'
		ctable['AO1P'] = 'εῖμεν'
		ctable['AO2P'] = 'εῖτε'
		ctable['AO3P'] = 'εῖεν'
	end
	
	dialform('PI3P', 'ησᾰν, εν', 'epi')
	dialform('PI', 'ῆναι/ήμεναι', 'epi')

	dialform('APF', 'ῆσᾰ', 'severe') -- 77.3
	dialform('APF', 'ένσᾰ', 'kre', 'arg')
	dialform('APF', 'ένσᾰ', 'the', 'ark')
	dialform('APF', 'εισᾰ', 'les')

	dialform('AS3P', 'εωντῐ', 'west') -- 138.4
	dialform('AS3P', 'εωνσῐ', 'ara')
	dialform('AS3P', 'ιωσῐ', 'kyp')
	dialform('AS3P', 'ιωνθῐ', 'boi')
	dialform('AS3P', 'εωνθῐ', 'the')
	dialform('AS3P', 'εῳσῐ', 'les')

	dialform('PI3P', 'εν', 'nonIA') -- 138.5

	dialform('AI', 'ην', 'les') -- 154, 155.3
	dialform('AI', 'ῆμεν', 'the', 'boi')
	dialform('AI', 'ῆμεν', 'west')
	dialform('AI', 'ήμην, ῆμεν', 'kre')
	dialform('AI', 'ήμειν', 'rho')
end

conjugations['aor-1'] = function()
	ctable = data.aor_1
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4
	
	if not_attic(args.dial) then
		ctable['MS2S'] = 'ηαι'
	end

	dialform('AO2S', 'αις, αισθᾰ, ειᾰς', 'epi')
	dialform('AI', 'αι/ᾰμεν/ᾰμεναι', 'epi')
	dialform('MO3P', 'αίᾰτο', 'epi')
	dialform('MI2S', 'ᾰο', 'epi')

	dialform('APM', 'αις', 'les') -- 77.3
	dialform('APF', 'αισᾰ', 'les')
	dialform('APF', 'ᾰ́νσᾰ', 'kre', 'arg')
	dialform('APF', 'ᾰ́νσᾰ', 'the', 'ark')

	dialform('AS3P', 'ωντῐ', 'west') -- 138.4
	dialform('AS3P', 'ωνσῐ', 'ara')
	dialform('AS3P', 'ωσῐ', 'kyp')
	dialform('AS3P', 'ωνθῐ', 'boi', 'the')
	
	dialform('AS2S', 'εις', 'les', 'kre') -- 150 (this is also East Ionic, which we don't have a code for)
	dialform('AS3S', 'ει', 'les', 'kre')
	dialform('AS2D', 'ετον', 'les', 'kre')
	dialform('AS3D', 'ετον', 'les', 'kre')
	dialform('AS1P', 'ομεν', 'les', 'kre')
	dialform('AS2P', 'ετε', 'les', 'kre')
	dialform('AS3P', 'οισῐ', 'les')
	dialform('AS3P', 'οντῐ', 'kre')
	dialform('MS1S', 'ομαι', 'les', 'kre')
	dialform('MS2S', 'εαι', 'les', 'kre')
	dialform('MS3S', 'εται', 'les', 'kre')
	dialform('MS2D', 'εσθον', 'les', 'kre')
	dialform('MS3D', 'εσθον', 'les', 'kre')
	dialform('MS1P', 'ομεθᾰ', 'les', 'kre')
	dialform('MS2P', 'εσθε', 'les', 'kre')
	dialform('MS3P', 'ονται', 'les', 'kre')

	dialform('AO2S', 'αις', 'nonIA') -- 152.4
	dialform('AO3S', 'αι', 'nonIA')
	dialform('AO3P', 'αιεν', 'nonIA')
	
--	dialform('AI', 'ειν', 'the') -- 156 - marked with (Larissa)
	
	dialforms_aorpass()
end

conjugations['aor-2'] = function()
	ctable = data.aor_2
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4
	
	-- not used:
	-- local mono = (m_accent.ult(stem2) == stem2)
	
	if not_attic(args.dial) then
		ctable['MI2S'] = 'εο'
		ctable['MS2S'] = 'ηαι'
		ctable['MC2S'] = 'εο' -- assuming from 426c that perispomenon only applies when contracted
	end

	dialform('AO2S', 'οις/οισθᾰ', 'epi')
	dialform('AI', 'εῖν/έμεν(αι)', 'epi')
	dialform('MO3P', 'οίᾰτο', 'epi')
	
	dialform('MI2S', 'ιο', 'buck9') -- 9
	dialform('MC2S', 'ίο', 'buck9')

	dialform('AS2D', 'ειτον', 'boi', 'the') -- 14
	dialform('AS3D', 'ειτον', 'boi', 'the')
	dialform('AS2P', 'ειτε', 'boi', 'the')
	dialform('MS2S', 'είαι', 'boi', 'the')
	dialform('MS3S', 'είται', 'boi', 'the')
	dialform('MS2D', 'εισθον', 'boi', 'the')
	dialform('MS3D', 'εισθον', 'boi', 'the')
	dialform('MS2P', 'εισθε', 'boi', 'the')

	dialform('AI2S', 'ῑς', 'boi') -- 28
	dialform('AI3S', 'ῑ', 'boi')
	dialform('AS2S', 'ῑς', 'boi') -- this is a conjecture
	dialform('AS3S', 'ῑ', 'boi')

	dialform('MI2S', 'εῦ', 'ion') -- 42.5
	dialform('MC2S', 'εῦ', 'ion')
	
	dialform('APF', 'ῶσᾰ', 'severe', 'boi') -- 77.3
	dialform('APF', 'όνσᾰ', 'kre', 'arg')
	dialform('APF', 'όνσᾰ', 'the', 'ark')
	dialform('APF', 'οισᾰ', 'les')

	dialform('AS3P', 'ωντῐ', 'west') -- 138.4
	dialform('AS3P', 'ωνσῐ', 'ara')
	dialform('AS3P', 'ωσῐ', 'kyp')
	dialform('AS3P', 'ωνθῐ', 'boi', 'the')
	dialform('AS3P', 'ῳσῐ', 'les')
	

	dialform('MC3P', 'όσθω', 'epd', 'lak') -- 140
	dialform('MC3P', 'ούσθω', 'kor')
	dialform('MC3P', 'όσθων', 'ato', 'ele')
	
	dialform('AS3S', 'η', 'ark') -- 149

	dialform('AI', 'ην', 'les') -- 153
	dialform('AI', 'εν', 'ark', 'del')
	dialform('AI', 'εν', 'doric')
	dialform('AI', 'ειν', 'krn', 'rho') -- exceptions to doric -εν
	dialform('AI', 'ην', 'ele', 'lak')
	dialform('AI', 'έμεν', 'boi', 'the') -- 155

	dialforms_aorpass()
end

conjugations['aor-emi'] = function()
	ctable = data.aor_emi
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4
	
	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'εῖτον'
		ctable['AO3D'] = 'είτην'
		ctable['AO1P'] = 'εῖμεν'
		ctable['AO2P'] = 'εῖτε'
		ctable['AO3P'] = 'εῖεν'
	end
	
	dialform('AI', 'έμεν(αι)', 'epi')
	
	dialform('AS1S', 'εω', 'nonIA')
	dialform('AS2S', 'ηαι', 'nonIA')
	dialform('AS1P', 'εωμεν', 'nonIA')
	dialform('MS1S', 'εωμαι', 'nonIA')
	dialform('MS1P', 'εωμεν', 'nonIA')
	dialform('MS3P', 'εωνται', 'nonIA')
	
	dialform('AS1S', 'ιω', 'buck9')
	dialform('AS1P', 'ιωμεν', 'buck9')
	dialform('MS1S', 'ιωμαι', 'buck9')
	dialform('MS1P', 'ιωμεν', 'buck9')
	dialform('MS3P', 'ιωνται', 'buck9')

	dialform('MO3S', 'εῖτο', 'nonIA')
	dialform('MO2D', 'εῖσθον', 'nonIA')
	dialform('MO3D', 'είσθην', 'nonIA')
	dialform('MO1P', 'είμεθᾰ', 'nonIA')
	dialform('MO2P', 'εῖσθε', 'nonIA')
	dialform('MO3P', 'εῖντο', 'nonIA')
	
	dialform('APF', 'ῆσᾰ', 'severe') -- 77.3
	dialform('APF', 'ένσᾰ', 'kre', 'arg')
	dialform('APF', 'ένσᾰ', 'the', 'ark')

	dialform('AS3P', 'εωντῐ', 'west') -- 138.4
	dialform('AS3P', 'εωνσῐ', 'ara')
	dialform('AS3P', 'ιωσῐ', 'kyp')
	dialform('AS3P', 'ιωνθῐ', 'boi')
	dialform('AS3P', 'εωνθῐ', 'the')
	dialform('AS3P', 'εῳσῐ', 'les')
	
	dialform('AI3P', 'εν', 'nonIA') -- 138.5

	dialform('AI', 'έμεναι', 'les') -- 154
	dialform('AI', 'έμεν', 'the', 'boi')
	dialform('AI', 'έμεν', 'west')
	dialform('AI', 'έμην, έμεν', 'kre')
	dialform('AI', 'έμειν', 'rho')
end

conjugations['aor-omi'] = function()
	ctable = data.aor_omi
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4

	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'οῖτον'
		ctable['AO3D'] = 'οίτην'
		ctable['AO1P'] = 'οῖμεν'
		ctable['AO2P'] = 'οῖτε'
		ctable['AO3P'] = 'οῖεν'
	end
	
	dialform('AI', 'όμεν(αι)', 'epi')

	dialform('APF', 'ῶσᾰ', 'severe', 'boi') -- 77.3
	dialform('APF', 'όνσᾰ', 'kre', 'arg')
	dialform('APF', 'όνσᾰ', 'the', 'ark')
	dialform('APM', 'οις', 'les')
	dialform('APF', 'οισᾰ', 'les')
	
	dialform('AS3P', 'ῶντῐ', 'west') -- 138.4
	dialform('AS3P', 'ῶνσῐ', 'ara')
	dialform('AS3P', 'ῶσῐ', 'kyp')
	dialform('AS3P', 'ῶνθῐ', 'boi', 'the')
	dialform('AS3P', 'ῳσῐ', 'les')

	dialform('AI3P', 'ον', 'nonIA') -- 138.5

	dialform('AI', 'όμεναι', 'les') -- 154
	dialform('AI', 'όμεν', 'the', 'boi')
	dialform('AI', 'όμεν', 'west')
	dialform('AI', 'όμην, όμεν', 'kre')
	dialform('AI', 'όμειν', 'rho')
end

conjugations['aor-amiw'] = function()
	require('debug').track('grc-conj/aor-amiw')
	ctable = data.aor_amiw
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4

	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'αῖτον'
		ctable['AO3D'] = 'αίτην'
		ctable['AO1P'] = 'αῖμεν'
		ctable['AO2P'] = 'αῖτε'
		ctable['AO3P'] = 'αῖεν'
	end
	
	dialform('APF', 'ᾰ́νσᾰ', 'kre', 'arg') -- 77.3
	dialform('APF', 'ᾰ́νσᾰ', 'the', 'ark')
	dialform('APM', 'αις', 'les')
	dialform('APF', 'αισᾰ', 'les')
	
	dialform('AS3P', 'ῶντῐ', 'west') -- 138.4
	dialform('AS3P', 'ῶνσῐ', 'ara')
	dialform('AS3P', 'ῶσῐ', 'kyp')
	dialform('AS3P', 'ῶνθῐ', 'boi', 'the')
	dialform('AS3P', 'ῳσῐ', 'les')

	dialform('AI3P', 'ᾰν', 'nonIA') -- 138.5

	dialform('AI', 'ᾰ́μεναι', 'les') -- 154
	dialform('AI', 'ᾰ́μεν', 'the', 'boi')
	dialform('AI', 'ᾰ́μεν', 'west')
	dialform('AI', 'ᾰ́μην, ᾰ́μεν', 'kre')
	dialform('AI', 'ᾰ́μειν', 'rho')
end

conjugations['aor-ami'] = function()
	require('debug').track('grc-conj/aor-ami')
	ctable = data.aor_ami
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4

	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'αῖτον'
		ctable['AO3D'] = 'αίτην'
		ctable['AO1P'] = 'αῖμεν'
		ctable['AO2P'] = 'αῖτε'
		ctable['AO3P'] = 'αῖεν'
	end
	
	dialform('AI', 'ᾰ́μεν(αι)', 'epi')
end

conjugations['aor-hmi'] = function()
	require('debug').track('grc-conj/aor-hmi')
	ctable = data.aor_hmi
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4
end

conjugations['aor-wmi'] = function()
	ctable = data.aor_wmi
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4
	
	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'οῖτον'
		ctable['AO3D'] = 'οίτην'
		ctable['AO1P'] = 'οῖμεν'
		ctable['AO2P'] = 'οῖτε'
		ctable['AO3P'] = 'οῖεν'
	end

	dialform('AI', 'ῶμεν/ώμεναι', 'epi')

	dialform('APF', 'ῶσᾰ', 'severe', 'boi') -- 77.3
	dialform('APF', 'όνσᾰ', 'kre', 'arg')
	dialform('APF', 'όνσᾰ', 'the', 'ark')
	dialform('APM', 'οις', 'les')
	dialform('APF', 'οισᾰ', 'les')
	
	dialform('AS3P', 'ῶντῐ', 'west') -- 138.4
	dialform('AS3P', 'ῶνσῐ', 'ara')
	dialform('AS3P', 'ῶσῐ', 'kyp')
	dialform('AS3P', 'ῶνθῐ', 'boi', 'the')
	dialform('AS3P', 'ῳσῐ', 'les')

	dialform('AI3P', 'ον', 'nonIA') -- 138.5

	dialform('AI', 'ώμεναι', 'les') -- 154
	dialform('AI', 'ῶμεν', 'the', 'boi')
	dialform('AI', 'ῶμεν', 'west')
	dialform('AI', 'ώμην, ῶμεν', 'kre')
	dialform('AI', 'ώμειν', 'rho')
end

conjugations['aor-numi'] = function()
	ctable = data.aor_numi
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4
end

conjugations['aor-hiemi-comp'] = function()
	ctable = data.aor_hiemic
	pctable = data.aor_pass
	pstem = stem3
	pstem2 = stem4
end

conjugations['aor-irreg'] = function()
	ctable = {}
	-- no aor-irregs have passive forms so we should be fine
	local i = 2
	for _, mood in ipairs({'I', 'S', 'O', 'C'}) do
		for person_number in iter_person_number() do
			args['A' .. mood .. person_number] = args['A' .. mood .. person_number] or args[i]
			i = i + 1
		end
	end
	args['AI'] = args['AI'] or args[34]
	args['APM'] = args['APM'] or args[35]
	args['APF'] = args['APF'] or args[36]
	args['APN'] = args['APN'] or args[37]
end

conjugations['perf'] = function()
	ctable = data.perf
	pstem = stem2
	
	if mw.ustring.match(m_accent.strip_accent(pstem), '[αεηιουω]$') then
		pstem = pstem .. 'V'
		ctable['MI3P'] = 'νται'
	end
	
	-- FIXME: In the dual and plural, the second form (εἶμεν for instance)
	-- is Attic and shouldn't be displayed in Ionic or Epic tables.
	local to_be_forms = {
		['S1S']='ὦ',
		['S2S']='ᾖς',
		['S3S']='ᾖ',
		['S2D']='ἦτον',
		['S3D']='ἦτον',
		['S1P']='ὦμεν',
		['S2P']='ἦτε',
		['S3P']='ὦσῐ(ν)',
		
		['O1S']='εἴην',
		['O2S']='εἴης',
		['O3S']='εἴη',
		['O2D']='εἴητον/εἶτον',
		['O3D']='εἰήτην/εἴτην',
		['O1P']='εἴημεν/εἶμεν',
		['O2P']='εἴητε/εἶτε',
		['O3P']='εἴησᾰν/εἶεν',
	}
	
	local mediopassive_participle = args['MPM'] and '*' .. args['MPM'] or ctable['MPM']
	local mediopassive_participle_stem = mediopassive_participle:gsub('ος$', '')
	if args['MPM'] then
		ctable['MPM'] = mediopassive_participle
	end
	ctable['MPF'] = mediopassive_participle_stem .. 'η'
	ctable['MPN'] = mediopassive_participle_stem .. 'ον'
	args['MPM'], args['MPF'], args['MPN'] = nil, nil, nil
	for code, form in pairs(to_be_forms) do
		local number = code:sub(-1)
		local ending = number == 'S' and 'ος'
			or number == 'D' and 'ω'
			or 'οι'
		-- No accent modification needed in the dual
		-- because the perfect passive participle has a non-recessive accent,
		-- on the penult.
		-- Add * to suppress addition of stem.
		local to_be_form = mw.ustring.gsub(
			form,
			'(()' .. word_character .. '+)',
			function(all, pos)
				-- Avoid adding * before ν in ὦσῐ(ν).
				local preceding = mw.ustring.sub(form, pos - 1, pos - 1)
				if preceding == '(' or preceding:find '%a' then
					return all
				else
					return '*' .. all
				end
			end)
		ctable['M' .. code] = mediopassive_participle_stem .. ending .. ' ' .. to_be_form
	end

	--active not found in Homer

	dialform('AI3P', 'ᾰτι, ᾰντῐ', 'west') -- 138.4, but no clear distinction?
	dialform('AI3P', 'ᾰσῐ', 'ark')
	dialform('AI3P', 'ᾰνθῐ', 'boi', 'the')

	dialform('AS3P', 'ωντῐ', 'west') -- 138.4
	dialform('AS3P', 'ωνσῐ', 'ara')
	dialform('AS3P', 'ωσῐ', 'kyp')
	dialform('AS3P', 'ωνθῐ', 'boi', 'the')
	dialform('AS3P', 'ῳσῐ', 'les')

	dialform('AI', 'ην', 'les') -- 147.2
	dialform('AI', 'εν', 'del', 'kre')
	dialform('AI', 'ειν', 'rho', 'epd')
	
	dialform('APM', 'ων', 'aio') -- 147.3
	dialform('APF', 'οισᾰ', 'les')
	dialform('APF', 'ονσᾰ', 'the')
	dialform('APF', 'ωσᾰ', 'boi')
	dialform('APN', 'ον', 'aio')
end

conjugations['plup'] = function()
	ctable = data.plup
	pstem = stem2
	
	if mw.ustring.match(m_accent.strip_accent(pstem), '[αεηιουω]$') then
		pstem = pstem .. 'V'
		ctable['MI3P'] = 'ντο'
	end

	dialform('AI3P', 'εν', 'nonIA')
end

conjugations['perf-ami'] = function()
	ctable = data.perf_ami

	if not_attic(args.dial) then
		-- this is never mentioned by Buck, but judging from Pharr the optative dual/plural with η is Attic only
		ctable['AO2D'] = 'αῖτον'
		ctable['AO3D'] = 'αίτην'
		ctable['AO1P'] = 'αῖμεν'
		ctable['AO2P'] = 'αῖτε'
		ctable['AO3P'] = 'αῖεν'
	end
	
	dialform('AI', 'ᾰ́μεν(αι)', 'epi')
	dialform('APM', 'ᾰώς', 'epi')
	dialform('APF', 'ᾰυῖᾰ', 'epi') -- pharr and smyth disagree here
	dialform('APN', 'ᾰός', 'epi')
end

conjugations['plup-ami'] = function()
	ctable = data.plup_ami
end

conjugations['perf-irreg'] = function()
	ctable = {}
	-- no perf-irregs have passive forms so we should be fine
	local i = 2
	for _, mood in ipairs({'I', 'S', 'O', 'C'}) do
		for person_number in iter_person_number() do
			args['A' .. mood .. person_number] = args['A' .. mood .. person_number] or args[i]
			i = i + 1
		end
	end
	args['AI'] = args['AI'] or args[34]
	args['APM'] = args['APM'] or args[35]
	args['APF'] = args['APF'] or args[36]
	args['APN'] = args['APN'] or args[37]
end

conjugations['plup-irreg'] = function()
	ctable = {}
	local i = 2
	for person_number in iter_person_number() do
		args['AI' .. person_number] = args['AI' .. person_number] or args[i]
		i = i + 1
	end
end

-- Functions for generating the inflection table

local aliases = {
	['pres'] = 'Present',
	['imperf'] = 'Imperfect',
	['fut'] = 'Future',
	['aor'] = 'Aorist',
	['perf'] = 'Perfect',
	['plup'] = 'Pluperfect',
	['futp'] = 'Future&nbsp;perfect',
	['active'] = 'A',
	['middle'] = 'M',
	['passive'] = 'P',
	['middle/<br>passive'] = 'M',
	['I'] = 'indicative',
	['S'] = 'subjunctive',
	['O'] = 'optative',
	['C'] = 'imperative',
}

local moods = {
	['pres'] = {'I', 'S', 'O', 'C'},
	['imperf'] = {'I'},
	['fut'] = {'I', 'O'},
	['aor'] = {'I', 'S', 'O', 'C'},
	['perf'] = {'I', 'S', 'O', 'C'},
	['plup'] = {'I'},
	['futp'] = {'I', 'O'},
}

local voices

local full_tense_name = {
	pres = 'present',
	imperf = 'imperfect',
	fut = 'future',
	aor = 'aorist',
	perf = 'perfect',
	plup = 'pluperfect',
	futp = 'future-perfect',
}
local function get_tense_class(tense)
	return 'grc-conj-' .. full_tense_name[tense]
end

-- Make the table
function make_table()
	voices = {'active', 'middle/<br>passive'}
	if args.form:match('act') then
		voices = {'active'}
	elseif args.form:match('mid') then
		voices = {'middle'}
	elseif args.form:match('pass') then
		voices = {'passive'}
	elseif args.form:match('am') then
		voices = {'active', 'middle'}
	elseif args.form:match('ap') then
		voices = {'active', 'passive'}
	elseif tense == 'fut' or tense == 'aor' then
		if args.form:match('mp') then
			voices = {'middle', 'passive'}
		else
			voices = {'active', 'middle', 'passive'}
		end
	elseif args.form:match('mp') then
		voices = {'middle/<br>passive'}
	end
	if tense ~= 'fut' and tense ~= 'aor' then
		aliases['passive'] = 'M'
	end
	
	local dialtitle = args.dial and "(" .. get_label_display(args.dial) .. ")" or nil
	return require('TemplateStyles')('Module:grc-conj/style.css')
.. [=[<div class="NavFrame">
<div class="NavHead">&nbsp; &nbsp;]=] .. aliases[tense] .. ': '
.. table.concat(get_title(), ', ') .. ' ' .. (args['titleapp'] or dialtitle or '') .. [=[</div>
<div class="NavContent">
<div class="center">
{| class="grc-conj ]=] .. get_tense_class(tense) .. [=["
|-
! colspan="2" class="grc-conj-number" | number
! colspan="3" class="grc-conj-number" | singular
! colspan="2" class="grc-conj-number" | dual
! colspan="3" class="grc-conj-number" | plural

]=] .. make_num_header(tense) .. make_rows() .. make_voice_header() .. make_nonfin_forms() .. make_notes() .. [=[

|}
</div></div></div>]=] .. categories
end

function get_title()
	local title = {}
	if conjtype == 'aor-emi' or conjtype == 'aor-omi' or conjtype == 'perf-ami' or conjtype == 'plup-ami' then
		table.insert(title, link_form('AI2D', 'true'))
	end
	for _, voice in ipairs(voices) do
		table.insert(title, link_form(aliases[voice] .. 'I1S', true) )
	end
	return title
end

local function full_link(term, alt, accel)
	return m_links.full_link{ lang = lang, term = term, alt = alt, tr = '-', accel = accel }
end

local target = nil

local get_contraction_map = require "fun".memoize(function (conjugation_code)
	if conjugation_code:match('con') then
		local vowel = conjugation_code:match('con%-(%a+)')
		local contraction_type
		if vowel == 'a' then
			if args.dial == 'boi' or dialgroups['west'][args.dial] then
				contraction_type = 'eta'
			else
				contraction_type = 'a'
			end
		elseif vowel == 'e' then
			if not not_attic(args.dial) then
				contraction_type = 'e'
			elseif args.dial == 'epi' or args.dial == 'ion' then
				contraction_type = 'e-epiion'
			elseif args.dial == 'boi' then
				contraction_type = 'e-boi'
			elseif dialgroups['buck9'][args.dial] then
				contraction_type = 'e-severe9'
			elseif dialgroups['severe'][args.dial] then
				contraction_type = 'e-severe'
			else
				contraction_type = 'e-nonatt'
			end
		else
			contraction_type = conjugation_code:match('con%-(.+)')
		end
		local contraction_map = contraction_types[contraction_type]
		if not contraction_map then
			error('Invalid contraction type: ' .. tostring(contraction_type))
		end
		return contraction_map
	end
	return false
end)

function link_form(form_code, istitle)
	local voice_code = form_code:sub(1, 1)
	local forms = (voice_code == 'P') and pctable or ctable
	local accel

	-- check that it's a valid voice
	local valid_voice
	for _, voice in ipairs(voices) do
		if aliases[voice] == voice_code then
			valid_voice = true
			break
		end
	end
	
	if not valid_voice then
		return nil
	end

	-- Get the form
	local form = forms[form_code]
	if (args[form_code] == nil) and (form == nil or form == '') then return nil end

	-- Apply contraction
	local contraction_map = get_contraction_map(conjtype)
	if contraction_map then
		form = mw.ustring.gsub(form, '[ÊĒÉĴĤḤÔŌÓÛÚŴẂÎĪÍ]', contraction_map)
	end
	
	form = dialforms_generic(form_code, form)

	-- Get the stem
	local stem = (voice_code == 'P') and pstem or stem
	if (tense == 'perf' or tense == 'plup') and voice_code == 'M' then stem = pstem end
	if tense == 'aor' and not form_code:match('.I..') then
		stem = (voice_code == 'P') and pstem2 or stem2
	end
	
	if args[form_code] then
		form = args[form_code]
		require('debug').track('grc-conj/form-override')
		if form == '' then return nil end
	end

	if (tense == 'perf' or tense == 'plup') and mw.ustring.match(form, '[MSTH]') then
		for _, replacements in pairs(perf_euph) do
			local pattern = replacements[1] .. '$'
			if mw.ustring.match(stem, pattern) then
				stem = mw.ustring.gsub(stem, pattern, '')
				for i, letter in ipairs({'M', 'S', 'T', 'H'}) do
					form = mw.ustring.gsub(form, letter, replacements[i + 1])
				end
				break
			end
		end
	end
	
	stem = mw.ustring.gsub(stem, 'V', '')

	form = mw.ustring.gsub(form, ', ', ',<br>')
	
	-- Link the form
	link = function(alt)
		local parenflag = false
		if mw.ustring.sub(alt, 1, 1) == '(' then
			parenflag = true
		end
		if parenflag then
			alt = mw.ustring.sub(alt, 2)
		elseif mw.ustring.sub(alt, 1, 1) == '*' then
			alt = mw.ustring.sub(alt, 2)
			return full_link(target, alt, accel)
		elseif not args[form_code] then
			alt = stem .. alt
		end
		--accentuate
		if not parenflag then
			if args.dial == 'les' then
				alt = m_accent.antepenult(alt)
			elseif form_code == 'APN' or form_code == 'AI'
					or (form_code == 'MI' and tense == 'perf') then
				alt = m_accent.pencirc(alt)
			elseif form_code == 'AO3S' and mw.ustring.match(alt, 'ι$') then
				alt = m_accent.penult(alt)
			-- if prefix has been provided and this is not a present or future or aorist non-indicative form
			elseif args['prefix'] and not (tense == 'pres' or tense == 'fut' or
					(tense == 'aor' and not form_code:find('.I..'))) then
				if alt:sub(1, #args['prefix']) ~= args['prefix'] then
					-- Safe to error here?
					mw.log('Beginning of stem ' .. alt .. " doesn't match prefix "
						.. args['prefix'] .. '.')
				end
				alt = args['prefix'] .. m_accent.antepenult(alt:sub(#args['prefix'] + 1))
			else
				alt = m_accent.antepenult(alt)
			end
		end
		
		--deal with parentheses
		if parenflag then
			target = target .. alt
		else
			target = alt
		end
		
		-- Fix sigma.
		target = mw.ustring.gsub(target, '[σς](.?)',
			function (after)
				if after == '' then
					return 'ς' .. after
				else
					return 'σ' .. after
				end
			end)
		
		return (parenflag and '(' or '') .. full_link(target, alt, accel)
	end
	
	if mw.ustring.match(form, 'με%(σ%)θᾰ$') then
		form = mw.ustring.toNFC(m_accent.antepenult(stem .. form))
		local me = form:gsub('%b().+', '') -- Remove parentheses, their contents, and everything after.
		local stha = form:gsub('[()]', '') -- Remove parentheses.
		local tha = form:gsub('%b()', '') -- Remove parentheses and their contents.
		form = full_link('[[' .. tha .. '|' .. me .. ']]([[' .. stha .. '|σ]])[['
			.. tha .. '|θᾰ]]', nil, accel)
	else
		form = mw.ustring.gsub(form, '(%(?' .. word_character .. '+)', link)
	end

	if istitle then
		form = mw.ustring.match(form, '[^,]+') -- capture up to comma
		form = mw.ustring.gsub(form, ' +$', '') -- strip final whitespace
	end
	
	return form
end

function make_num_header(tense)
	local class = get_tense_class(tense)
	local header = '|-\n! colspan="2" |\n'
	for _, person in ipairs({'first', 'second', 'third', 'second', 'third', 'first', 'second', 'third'}) do
		header = header .. '! class="grc-conj-person" |' .. person .. '\n'
	end
	return header
end

function make_rows()
	local rows = ''
	local lmoods = args['indonly'] and {'I'} or moods[tense]
	local class = get_tense_class(tense)
	for _, voice in pairs(voices) do
		rows = rows .. '|-\n! rowspan="' .. #lmoods .. '" | ' .. voice .. '\n\n'
		for i, mood in ipairs(lmoods) do
			if i ~= 1 then rows = rows .. '|-\n' end
			rows = rows .. '! ' .. aliases[mood] .. '\n'
			for person_number in iter_person_number() do
				if aliases[voice] == nil then error(voice) end
				code = aliases[voice] .. mood .. person_number
				rows = rows .. '| class="grc-conj-finite-form" | ' .. (link_form(code) or '&nbsp;') .. '\n'
			end
		end
	end
	contractnote = mw.ustring.match(rows, '†')
	return rows
end

function make_voice_header()
	-- not used:
	-- local form = args.form
	local header = ''
	if tense == 'imperf' or tense == 'plup' or args['indonly'] then
		return header
	end
	header = '|-\n! colspan="2" |'
	local class = get_tense_class(tense)
	if tense == 'fut' or tense == 'aor' then
		header = header .. '\n! colspan="3" | '
		if voices[1] == 'active' then header = header .. 'active' end
		header = header .. '\n! colspan="2" | '
		if voices[2] == 'middle' or voices[1] == 'middle' then header = header .. 'middle' end
		header = header .. '\n! colspan="3" | '
		if voices[1] == 'passive' or voices[2] == 'passive' or voices[3] == 'passive' then header = header .. 'passive' end
	else
		header = header .. '\n! colspan="4" | '
		if voices[1] == 'active' then header = header .. 'active' end
		header = header .. '\n! colspan="4" | '
		if voices[1] == 'middle/<br>passive' or voices[2] == 'middle/<br>passive' then header = header .. 'middle/passive' end
	end
	header = header .. '\n'
	return header
end

function make_nonfin_forms()
	if tense == 'imperf' or tense == 'plup' or args['indonly'] then
		return ''
	end
	local class = get_tense_class(tense)
	local output = '|-\n! colspan="2" | infinitive\n'
	local flag = (tense == 'fut' or tense == 'aor')
	output = output .. '| colspan="' .. (flag and 3 or 4) .. '" class="grc-conj-nonfinite-form" | ' .. (link_form('AI') or '') .. '\n'
	output = output .. '| colspan="' .. (flag and 2 or 4) .. '" class="grc-conj-nonfinite-form" | ' .. (link_form('MI') or '') .. '\n'
	if flag then
		output = output .. '| colspan="3" class="grc-conj-nonfinite-form" | ' .. (link_form('PI') or '') .. '\n'
	end
	output = output .. '|-\n! rowspan="3" class="grc-conj-nonfinite-form" | participle\n'
	for _, gender in ipairs({'m', 'f', 'n'}) do
		if gender ~= 'm' then output = output .. '|-\n' end
		output = output .. '! ' .. gender .. '\n'
		output = output .. '| colspan="' .. (flag and 3 or 4) .. '" class="grc-conj-nonfinite-form" | ' .. (link_form('AP' .. string.upper(gender) ) or '') .. '\n'
		output = output .. '| colspan="' .. (flag and 2 or 4) .. '" class="grc-conj-nonfinite-form" | ' .. (link_form('MP' .. string.upper(gender) ) or '') .. '\n'
		if flag then
			output = output .. '| colspan="3" class="grc-conj-nonfinite-form" | ' .. (link_form('PP' .. string.upper(gender) ) or '') .. '\n'
		end
	end
	return output
end

function make_notes()
	local notes = args.notes or ''
    if notes ~= '' then
        notes = '\n' .. notes
    end
	if contractnote then
		notes = '† [[Appendix:Ancient Greek contraction|contracted]]' .. notes -- should go first
	end

	if args.dial ~= 'koi' and args.dial ~= 'gkm' then
		if args.dial and args.dial ~= 'att' then
			notes = 'Dialects other than Attic are not well attested. '
				.. 'Some forms are based on conjecture. Use with caution. '
				.. 'For more details, see [[Appendix:Ancient Greek dialectal conjugation]].' .. notes
		else
			notes = 'This table gives Attic inflectional endings. '
				.. 'For conjugation in dialects other than Attic, see '
				.. '[[Appendix:Ancient Greek dialectal conjugation]].' .. notes
		end
	end
	if notes == '' then
		return ''
	end
	return [[
|-
! class="grc-conj-notes-header | Notes:
| class="grc-conj-notes" colspan="13" | ]] .. [[<div class="use-with-mention">]] .. notes .. [[</div>]]
end

return export
