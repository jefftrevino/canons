# !/usr/bin/env python
"""
Canon Generator
A tool for creating n-voice prolation canons from a melody
"""


import abjad
import fractions
from typing import List, Optional, Union
import time
import functools


class CanonGenerator:
    """
    Generates n-voice prolation canons at specified diatonic intervals.
    """
    
    def __init__(
        self,
        melody_staff: abjad.Staff,
        voice_count: int = 3,
        transposition_interval: int = -12,  # Default: octave down
        prolation_factor: Union[int, float, fractions.Fraction] = 2,
        time_signature: tuple = (3, 4),  # Default: 3/4 time
        debug: bool = False
    ):
        """
        Initialize the CanonGenerator.
        
        Args:
            melody_staff: An Abjad Staff containing the melody
            voice_count: Number of voices in the canon
            transposition_interval: Interval for transposition (in semitones)
            prolation_factor: Factor by which each voice is slower than the previous
            time_signature: Time signature as a tuple (numerator, denominator)
            debug: Enable debug output
        """
        self.melody_staff = melody_staff
        self.voice_count = voice_count
        self.transposition_interval = transposition_interval
        self.prolation_factor = fractions.Fraction(prolation_factor)
        self.time_signature = time_signature
        self.debug = debug
        self.melody_duration = abjad.get.duration(melody_staff)
        
        # Store the original LilyPond string for recovery
        self.original_lilypond = abjad.lilypond(melody_staff)
        
        if self.debug:
            print("=== CANON GENERATOR INITIALIZED ===")
            print(f"Voice count: {self.voice_count}")
            print(f"Transposition interval: {self.transposition_interval} semitones")
            print(f"Prolation factor: {self.prolation_factor}")
            print(f"Time signature: {self.time_signature}")
            print(f"Original LilyPond:\n{self.original_lilypond}")
    
    def _extract_pitches_and_durations(self) -> tuple[List, List]:
        """
        Extract pitches and durations from the melody staff.
        
        Returns:
            Tuple of (pitches, durations)
        """
        pitches = []
        durations = []
        
        for leaf in abjad.select.leaves(self.melody_staff):
            if isinstance(leaf, abjad.Note):
                pitches.append(leaf.written_pitch())
                durations.append(leaf.written_duration())
            elif isinstance(leaf, abjad.Rest):
                pitches.append(None)
                durations.append(leaf.written_duration())
            elif isinstance(leaf, abjad.Chord):
                # For chords, take all pitches as a list
                pitches.append([p for p in leaf.written_pitches()])
                durations.append(leaf.written_duration())
        
        if self.debug:
            print("\n=== EXTRACTED PITCHES AND DURATIONS ===")
            print(f"Number of pitches: {len(pitches)}")
            print(f"Number of durations: {len(durations)}")
            print(f"First 5 pitches: {pitches[:5]}")
            print(f"First 5 durations: {durations[:5]}")
        
        return pitches, durations
    
    def _create_prolated_durations(self, durations: List) -> List[List]:
        """
        Create prolated durations for each voice.
        
        Args:
            durations: Original durations from the melody
            
        Returns:
            List of duration lists, one for each voice
        """
        prolated_durations = []
        
        for voice_index in range(self.voice_count):
            factor = self.prolation_factor ** voice_index
            voice_durations = []
            
            for duration in durations:
                # Multiply duration by the prolation factor
                new_duration = abjad.Duration(duration) * factor
                voice_durations.append(new_duration)
            
            prolated_durations.append(voice_durations)
            
            if self.debug:
                print(f"\n=== VOICE {voice_index} DURATIONS ===")
                print(f"Prolation factor: {factor}")
                print(f"First 5 durations: {voice_durations[:5]}")
                print(f"Total duration: {sum(voice_durations)}")
        
        return prolated_durations

    
    def _create_transposed_pitches(self, pitches: List) -> List[List]:
        """
        Create transposed pitches for each voice.
        
        Args:
            pitches: Original pitches from the melody
            
        Returns:
            List of pitch lists, one for each voice
        """
        transposed_pitches = []
        
        for voice_index in range(self.voice_count):
            voice_pitches = []
            transposition_amount = self.transposition_interval * voice_index
            
            for pitch in pitches:
                if pitch is None:  # Rest
                    voice_pitches.append(None)
                elif isinstance(pitch, list):  # Chord
                    transposed_chord = []
                    for p in pitch:
                        new_pitch = p.transpose(transposition_amount)
                        transposed_chord.append(new_pitch)
                    voice_pitches.append(transposed_chord)
                else:  # Single note
                    new_pitch = pitch.transpose(transposition_amount)
                    voice_pitches.append(new_pitch)
            
            transposed_pitches.append(voice_pitches)
            
            if self.debug:
                print(f"\n=== VOICE {voice_index} PITCHES ===")
                print(f"Transposition: {transposition_amount} semitones")
                print(f"First 5 pitches: {voice_pitches[:5]}")
        
        return transposed_pitches
    
    def _create_voice_notes(self, pitches: List, durations: List) -> List:
        """
        Create notes from pitches and durations for a single voice.
        
        Args:
            pitches: List of pitches for the voice
            durations: List of durations for the voice
            
        Returns:
            List of Note/Rest objects
        """
        notes = []
        
        for pitch, duration in zip(pitches, durations):
            durations = self._long_duration_to_measure_sized_durations(duration)
            if pitch is None:
                # Create a rest using make_leaves with nested empty list
                rest = abjad.makers.make_leaves([[]], [duration])
                notes.extend(rest)
            else:
                # Use make_leaves with proper nesting
                # For a single note, pitch needs to be wrapped in a list
                # For a chord (list of pitches), it's already a list
                if isinstance(pitch, list):
                    # It's already a list (chord)
                    made_notes = abjad.makers.make_leaves([pitch], durations)
                else:
                    # Single pitch - needs to be wrapped in a list
                    made_notes = abjad.makers.make_leaves([[pitch]], durations)
                    if 1 < len(made_notes):
                        abjad.tie(made_notes)
                notes.extend(made_notes)
        
        return notes
    
    
    def _add_clefs(self, score: abjad.Score) -> None:
        """
        Add appropriate clefs to voices for better legibility.
        Uses treble clef for the first voice, bass clef for lower voices.
        
        Args:
            score: The score to process
        """
        staves = abjad.select.components(score, abjad.Staff)
        for voice_index, staff in enumerate(staves):
            first_leaf = abjad.select.leaf(staff, 0)
            # Use treble clef for the first voice, bass clef for others
            clef_type = "treble" if voice_index == 0 else "bass"
            clef = abjad.Clef(clef_type)
            abjad.attach(clef, first_leaf)
            if self.debug:
                print(f"Added {clef_type} clef to voice {voice_index}")

    def _add_time_signatures(self, score: abjad.Score) -> None:
        """
        Attach the specified time signature to the first leaf of each staff.
        """
        staves = abjad.select.components(score, abjad.Staff)
        for staff in staves:
            first_leaf = abjad.select.leaf(staff, 0)
            if first_leaf is not None:
                time_signature = abjad.TimeSignature(self.time_signature)
                abjad.attach(time_signature, first_leaf)
            if self.debug:
                print(f"Added time signature {self.time_signature} to staff {staff.name}")
            # Voice 0 (original pitch) stays in treble clef by default
            
            # Voice 0 (original pitch) stays in treble clef by default
    
    def generate(self) -> abjad.Score:
        """
        Generate the canon score.
        
        Returns:
            An Abjad Score object containing the canon
        """
        if self.debug:
            print("\n=== GENERATING CANON ===")
        
        # Step 1: Extract pitches and durations from melody
        pitches, durations = self._extract_pitches_and_durations()
        
        # Step 2: Create prolated durations for each voice
        prolated_durations = self._create_prolated_durations(durations)
        
        # Step 3: Create transposed pitches for each voice
        transposed_pitches = self._create_transposed_pitches(pitches)
        
        # Step 4: Create notes for each voice.
        notes_per_voice = []
        for pitches, durations in zip(transposed_pitches, prolated_durations):
            notes = self._create_voice_notes(pitches, durations)
            notes_per_voice.append(notes)
        
        # Step 5: Create the score with all voices
        # by repeating the melody in each voice

        # make an empty score
        score = abjad.Score()
        for i in range(self.voice_count):
            # Create a staff for each voice
            staff = abjad.Staff(name=f"Staff_{i}")
            score.append(staff)

        top_voice_index = self.voice_count - 1
        # for each each entering voice
        for entering_voice_index in range(self.voice_count): # 0, 1, 2
            print(f"voice　{entering_voice_index} entering")
            rest_duration = sum(prolated_durations[entering_voice_index])       
            for staff_index in range(0, self.voice_count): # 0, 1, 2
                # if repetition exponent is >= 0, we repeat the notes
                # else we add rests
                repetition_exponent = entering_voice_index - staff_index
                if repetition_exponent < 0:
                    print(f"adding rests to staff {staff_index} for voice {entering_voice_index}")
                    # Add rests for this staff
                    rests = self._long_rest_to_measure_sized_rests(rest_duration)
                    score[staff_index].extend(rests)
                else:
                    print(f"adding notes to staff {staff_index} for voice {entering_voice_index}")
                    # Add notes for this staff
                    # Repeat the notes for this voice
                    # according to the repetition exponent
                    num_occurrences = 2 ** repetition_exponent
                    repeated_notes = []
                    for _ in range(num_occurrences):
                        repeated_notes = [abjad.Note(n) for n in notes_per_voice[staff_index]]
                        score[staff_index].extend(repeated_notes)
        
        
        # add clefs and time signatures
        self._add_clefs(score)
        self._add_time_signatures(score)

        # split and fuse the staves
        for staff in score:
            # split staff at measure boundaries
            self._split_and_fuse_staff(staff)

        return score

    def _long_rest_to_measure_sized_rests(self, rest_duration):
        # Split rest_duration into measure-sized chunks
        measure_duration = abjad.Duration(self.time_signature)
        remaining = rest_duration
        rest_durations = []
        while remaining > 0:
            d = min(measure_duration, remaining)
            rest_durations.append(d)
            remaining -= d
        rests = abjad.makers.make_leaves([[]], rest_durations)
        return rests
    
    def _long_duration_to_measure_sized_durations(self, duration):
        # Split duration into measure-sized chunks
        measure_duration = abjad.Duration(self.time_signature)
        remaining = duration
        durations = []
        while remaining > 0:
            d = min(measure_duration, remaining)
            durations.append(d)
            remaining -= d
        return durations
    
    def _split_and_fuse_staff(self, staff):
            # split staff at measure boundaries
            abjad.mutate.split(staff[:], [self.time_signature], cyclic=True)
            # and then fuse according to 3/4 meter within each measure
            tree = abjad.meter.make_best_guess_rtc(self.time_signature)
            meter = abjad.meter.Meter(tree)
            staff_leaves = abjad.select.leaves(staff)
            measures =  abjad.select.group_by_measure(staff_leaves)
            for measure in measures:
                meter.rewrite(measure[:])
            
    def write_lilypond(self, filename: str = "canon.ly", score: Optional[abjad.Score] = None):
        """
        Write the canon to a LilyPond file.

        Args:
            filename: Output filename
            score: Abjad Score object to write (if None, regenerate)
        """
        if score is None:
            score = self.generate()

        lilypond_file = abjad.LilyPondFile([score])

        with open(filename, 'w') as f:
            f.write(abjad.lilypond(lilypond_file))

        if self.debug:
            print(f"\n=== WROTE LILYPOND FILE: {filename} ===")

        return lilypond_file


# Test code
if __name__ == "__main__":
    # Korean folk song "Arirang" in 3/4 time, key of A major
    arirang_lilypond = "e'4.( fs'8 e'4 a'4. b'8 a' b' cs''4 b'8 cs''16 b' a'8 fs' e'4.) fs'8( e' fs' a'4. b'8 a' b' cs'' b' a' fs' e' fs' a'4. b'8 a'4 a'2.) e''2( e''4 e'' cs'' b' cs'' b'8 cs''16 b' a'8 fs' e'4.) fs'8( e' fs' a'4. b'8 a' b' cs'' b' a' fs' e' fs' a'4. b'8 a'4 a'2.)"
    
    # Create melody staff
    melody_staff = abjad.Staff(arirang_lilypond)

    
    # Create canon generator with debug mode
    generator = CanonGenerator(
        melody_staff=melody_staff,
        voice_count=5,
        transposition_interval=-12,  # Octave down
        prolation_factor=2,
        time_signature=(3, 4),  # 3/4 time for Arirang
        debug=False
    )
    
    # Generate the canon
    canon_score = generator.generate()
    
    # Write to file
    generator.write_lilypond("canon.ly", canon_score)
    
    # Show the score (if running interactively)
    # abjad.show(canon_score)
    
    print("\n=== TEST COMPLETE ===")
    print("Canon generated successfully!")
    print("Output written to canon.ly")