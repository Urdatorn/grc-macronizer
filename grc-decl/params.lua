local m_table = require("table")

local deepcopy = m_table.deepcopy

local genders = { 'M', 'F', 'N' }
local cases = { 'N', 'G', 'D', 'A', 'V' }
local numbers = { 'S', 'D', 'P' }

local noun_params = {
	[1] = {},
	[2] = {},
	dial = { default = 'att' },
	form = { default = 'full' },
	voc = {}, -- if "α", means that first-declension masculine has vocative in -ᾰ
	notes = {},
	note = { alias_of = "notes" },
	['notes1'] = {},
	['notes2'] = {},
	titleapp = {},
	['titleapp1'] = {},
	['titleapp2'] = {},
}

for _, c in ipairs(cases) do
	for _, n in ipairs(numbers) do
		noun_params[c .. n] = {}
		noun_params[c .. n .. 1] = {}
		noun_params[c .. n .. 2] = {}
	end
end

local irreg_noun_params, irreg_N_noun_params = deepcopy(noun_params), deepcopy(noun_params)
for i = 3, 9 do
	irreg_N_noun_params[i] = {}
end
for i = 3, 12 do
	irreg_noun_params[i] = {}
end

local adj_params = {
	[1] = {},
	[2] = {},
	dial = { default = 'att' },
	form = { default = '' },
	notes = {},
	['notes1'] = {},
	['notes2'] = {},
	titleapp = {},
	['titleapp1'] = {},
	['titleapp2'] = {},
	title = {},
	adv = {},
	['adv1'] = {},
	['adv2'] = {},
	deg = {},
	comp = {},
	['comp1'] = {},
	['comp2'] = {},
	super = {},
	['super1'] = {},
	['super2'] = {},
	hp = { type = "boolean" },
}

for _, g in ipairs(genders) do
	for _, c in ipairs(cases) do
		for _, n in ipairs(numbers) do
			adj_params[g .. c .. n] = {}
			adj_params[g .. c .. n .. 1] = {}
			adj_params[g .. c .. n .. 2] = {}
		end
	end
end

local irreg_adj_params = deepcopy(adj_params)
for i = 3, 25 do
	irreg_adj_params[i] = {}
end

return {
	noun_params = noun_params,
	irreg_noun_params = irreg_noun_params,
	irreg_N_noun_params = irreg_N_noun_params,
	adj_params = adj_params,
	irreg_adj_params = irreg_adj_params,
}