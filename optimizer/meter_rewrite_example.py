import abjad

staff = abjad.Staff("c'1.")
abjad.mutate.split(staff[:], [(3, 4)], cyclic=True)
print(abjad.lilypond(staff))