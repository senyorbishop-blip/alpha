# Character Builder QA Checklist — Post Stage 1-9

## New Character Flow
- [ ] Open builder → Identity step loads
- [ ] Species step shows cards (not dropdown)
- [ ] Can select each of the 13+ species
- [ ] Selected species shows full trait details
- [ ] Class step shows cards with hit die, armor, role description
- [ ] Selecting Fighter shows 20-level progression table
- [ ] Selecting Wizard shows spell slot table
- [ ] Abilities step has all 4 methods: Roll, Standard Array, Point Buy, Manual
- [ ] Point Buy tracks spent points correctly
- [ ] Origins step shows background cards
- [ ] Selecting Soldier background auto-fills skills: Athletics, Intimidation
- [ ] Spells step filters by class (Wizard sees wizard spells only)
- [ ] Spell browser has search and school filter
- [ ] Equipment step shows class starting equipment options as checkboxes
- [ ] Review step shows computed AC, HP, initiative, passive perception
- [ ] Review step shows all 6 saves with correct proficiency marks
- [ ] Save Character writes to database successfully

## Level Up Flow
- [ ] Character at level 1 can initiate level up
- [ ] Level 2 Fighter sees: Action Surge feature description
- [ ] Level 4 Fighter sees ASI picker (not just a text box)
- [ ] ASI picker lets you +2 one stat or +1 two stats or pick a feat
- [ ] Feat picker is searchable and shows descriptions
- [ ] Level up writes new level to character document
- [ ] HP is recalculated after level up

## Integration
- [ ] After creating character, dice modifier dropdown shows stats
- [ ] Rolling d20 with STR modifier selected shows "+STR (+2)" in result
- [ ] Character token on map shows correct HP and AC from character sheet
- [ ] Inventory carry capacity shows correct value based on STR score
- [ ] Encumbrance warning appears at correct weight threshold

## New Player Experience
- [ ] Every section has a ? tooltip button
- [ ] Tooltip text is accurate and helpful for newcomers
- [ ] Class cards show role description before selection
- [ ] Standard Array method has clear instructions
- [ ] Spell browser has descriptions that a new player can understand
- [ ] Review step stat block is readable and makes sense without D&D knowledge
