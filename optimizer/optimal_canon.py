import abjad
from fractions import Fraction
from typing import List, Tuple, Dict, Optional

class Rubric:
    """
    Defines scoring criteria for canon evaluation.
    """
    
    def __init__(self, 
                 strong_beat_consonance: float = 5.0,
                 medium_beat_consonance: float = 2.0,
                 weak_beat_consonance: float = 1.0,
                 strong_beat_unison_penalty: float = -2.0,
                 medium_beat_unison_penalty: float = -1.0,
                 weak_beat_unison_penalty: float = -0.5,
                 strong_beat_dissonance_penalty: float = -1.0,
                 medium_beat_dissonance_penalty: float = -0.5,
                 weak_beat_dissonance_penalty: float = 0.0,
                 overall_consonance_bonus: float = 10.0):
        """
        Initialize scoring rubric.
        """
        self.strong_beat_consonance = strong_beat_consonance
        self.medium_beat_consonance = medium_beat_consonance
        self.weak_beat_consonance = weak_beat_consonance
        
        self.strong_beat_unison_penalty = strong_beat_unison_penalty
        self.medium_beat_unison_penalty = medium_beat_unison_penalty
        self.weak_beat_unison_penalty = weak_beat_unison_penalty
        
        self.strong_beat_dissonance_penalty = strong_beat_dissonance_penalty
        self.medium_beat_dissonance_penalty = medium_beat_dissonance_penalty
        self.weak_beat_dissonance_penalty = weak_beat_dissonance_penalty
        
        self.overall_consonance_bonus = overall_consonance_bonus

class Judge:
    """
    Evaluates canon scores according to a given rubric.
    """
    
    def __init__(self, rubric: Rubric, time_signature: abjad.TimeSignature, debug: bool = False):
        """
        Initialize judge with scoring rubric.
        """
        self.rubric = rubric
        self.time_signature = time_signature
        self.meter = self._create_meter_from_time_signature(time_signature)
        self.debug = debug
        
        # Define consonant intervals
        self.consonant_intervals = {
            'P1', 'P8', 'P5', 'P4',  # Perfect consonances
            'M3', 'm3', 'M6', 'm6'   # Imperfect consonances
        }
        
        self.consonant_interval_classes = {
            0, 7, 5, 4, 3, 8, 9  # Semitone classes
        }
    
    def _create_meter_from_time_signature(self, time_signature: abjad.TimeSignature) -> abjad.Meter:
        """
        Create an Abjad Meter from a time signature using rhythm tree strings.
        
        Args:
            time_signature: The time signature to convert
            
        Returns:
            abjad.Meter instance with proper metrical hierarchy
        """
        numerator = time_signature.numerator
        denominator = time_signature.denominator
        
        # Create rhythm tree using string parsing for common meters
        if numerator == 2 and denominator == 4:
            # 2/4: Simple duple meter
            string = "(2/4 (1/4 1/4))"
            
        elif numerator == 3 and denominator == 4:
            # 3/4: Simple triple meter
            string = "(3/4 (1/4 1/4 1/4))"
            
        elif numerator == 4 and denominator == 4:
            # 4/4: Hierarchical structure with strong-weak / medium-weak grouping
            string = "(4/4 ((2/4 (1/4 1/4)) (2/4 (1/4 1/4))))"
            
        elif numerator == 6 and denominator == 8:
            # 6/8: Compound duple meter with two dotted-quarter groupings
            string = "(6/8 ((3/8 (1/8 1/8 1/8)) (3/8 (1/8 1/8 1/8))))"
            
        elif numerator == 9 and denominator == 8:
            # 9/8: Compound triple meter
            string = "(9/8 ((3/8 (1/8 1/8 1/8)) (3/8 (1/8 1/8 1/8)) (3/8 (1/8 1/8 1/8))))"
            
        elif numerator == 12 and denominator == 8:
            # 12/8: Compound quadruple meter
            string = "(12/8 ((3/8 (1/8 1/8 1/8)) (3/8 (1/8 1/8 1/8)) (3/8 (1/8 1/8 1/8)) (3/8 (1/8 1/8 1/8))))"
            
        elif numerator == 5 and denominator == 4:
            # 5/4: Asymmetrical meter - can be grouped 3+2 or 2+3
            string = "(5/4 ((3/4 (1/4 1/4 1/4)) (2/4 (1/4 1/4))))"
            
        elif numerator == 7 and denominator == 8:
            # 7/8: Asymmetrical meter - can be grouped 3+2+2 or 2+3+2 or 2+2+3
            string = "(7/8 ((3/8 (1/8 1/8 1/8)) (2/8 (1/8 1/8)) (2/8 (1/8 1/8))))"
            
        else:
            # Generic fallback for other time signatures - simple flat structure
            beat_unit = f"1/{denominator}"
            beats = " ".join([beat_unit] * numerator)
            string = f"({numerator}/{denominator} ({beats}))"
        
        # Parse the string to create rhythm tree container
        rhythm_tree_container = abjad.rhythmtrees.parse(string)[0]  # Extract first element from list
        
        return abjad.Meter(rhythm_tree_container)
    
    def get_beat_strength(self, offset: Fraction) -> str:
        """Determine beat strength at given offset."""
        beats_per_measure = self.time_signature.numerator
        beat_duration = Fraction(1, self.time_signature.denominator)
        
        position_in_measure = offset % (beats_per_measure * beat_duration)
        beat_number = int(position_in_measure / beat_duration)
        
        # This old line should be removed - using meter instead
        # template_index = beat_number % len(self.beat_template)
        # return self.beat_template[template_index]
        
        # Use the meter-based approach instead
        try:
            measure_duration = Fraction(self.time_signature.numerator, self.time_signature.denominator)
            normalized_offset = offset % measure_duration
            beat_depth = self.meter.beat_depth_at_offset(normalized_offset)
            
            if beat_depth == 0:
                return 'S'
            elif beat_depth == 1:
                return 'm'
            else:
                return 'w'
        except:
            # Fallback
            if beat_number == 0:
                return 'S'
            else:
                return 'w'
    
    def calculate_interval(self, pitch1: abjad.NamedPitch, pitch2: abjad.NamedPitch) -> str:
        """Calculate interval between two pitches."""
        try:
            interval = abjad.NamedInterval.from_pitch_carriers(pitch1, pitch2)
            return interval.name()
        except:
            semitones = abs(pitch1.number() - pitch2.number()) % 12
            interval_map = {
                0: 'P1', 1: 'm2', 2: 'M2', 3: 'm3', 4: 'M3', 5: 'P4',
                6: 'TT', 7: 'P5', 8: 'm6', 9: 'M6', 10: 'm7', 11: 'M7'
            }
            return interval_map.get(semitones, 'unknown')
    
    def is_consonant(self, interval_name: str) -> bool:
        """Check if interval is consonant."""
        if interval_name in self.consonant_intervals:
            return True
            
        semitone_map = {
            'P1': 0, 'm2': 1, 'M2': 2, 'm3': 3, 'M3': 4, 'P4': 5,
            'TT': 6, 'P5': 7, 'm6': 8, 'M6': 9, 'm7': 10, 'M7': 11
        }
        
        if interval_name in semitone_map:
            semitones = semitone_map[interval_name]
            return semitones in self.consonant_interval_classes
            
        return False
    
    def is_unison(self, interval_name: str) -> bool:
        """Check if interval is a unison (P1 or P8)."""
        return interval_name in ['P1', 'P8']
    
    def evaluate_score(self, score: abjad.Score) -> float:
        """
        Evaluate a score according to the rubric.
        
        Returns:
            Float score (higher is better)
        """
        total_score = 0.0
        moment_count = 0
        strong_beat_consonances = 0
        strong_beat_moments = 0
        interval_analysis = []
        
        for moment in abjad.iterate_vertical_moments(score):
            leaves = moment.leaves()
            if len(leaves) < 2:
                continue
                
            moment_count += 1
            beat_strength = self.get_beat_strength(moment.offset())
            
            # Analyze intervals at this moment
            consonances = 0
            dissonances = 0
            unisons = 0
            total_pairs = 0
            moment_intervals = []
            
            for i, leaf1 in enumerate(leaves):
                for leaf2 in leaves[i+1:]:
                    if isinstance(leaf1, abjad.Note) and isinstance(leaf2, abjad.Note):
                        interval = self.calculate_interval(leaf1.written_pitch(), leaf2.written_pitch())
                        is_cons = self.is_consonant(interval)
                        is_unis = self.is_unison(interval)
                        
                        total_pairs += 1
                        moment_intervals.append((leaf1.written_pitch(), leaf2.written_pitch(), interval, is_cons, is_unis))
                        
                        if is_unis:
                            unisons += 1
                        elif is_cons:
                            consonances += 1
                        else:
                            dissonances += 1
            
            # Store for debugging
            interval_analysis.append({
                'offset': moment.offset(),
                'beat_strength': beat_strength,
                'intervals': moment_intervals,
                'consonances': consonances,
                'dissonances': dissonances,
                'unisons': unisons,
                'pairs': total_pairs
            })
            
            # Apply scoring based on beat strength and rubric
            if total_pairs > 0:
                moment_score = 0.0
                
                # Get scoring weights based on beat strength
                if beat_strength == 'S':
                    cons_weight = self.rubric.strong_beat_consonance
                    diss_weight = self.rubric.strong_beat_dissonance_penalty
                    unis_weight = self.rubric.strong_beat_unison_penalty
                    strong_beat_consonances += consonances
                    strong_beat_moments += total_pairs
                elif beat_strength == 'm':
                    cons_weight = self.rubric.medium_beat_consonance
                    diss_weight = self.rubric.medium_beat_dissonance_penalty
                    unis_weight = self.rubric.medium_beat_unison_penalty
                else:  # weak
                    cons_weight = self.rubric.weak_beat_consonance
                    diss_weight = self.rubric.weak_beat_dissonance_penalty
                    unis_weight = self.rubric.weak_beat_unison_penalty
                
                # Calculate moment score
                moment_score = (consonances * cons_weight + 
                              dissonances * diss_weight + 
                              unisons * unis_weight)
                
                total_score += moment_score
        
        # Add overall consonance bonus
        if strong_beat_moments > 0:
            strong_beat_ratio = strong_beat_consonances / strong_beat_moments
            total_score += strong_beat_ratio * self.rubric.overall_consonance_bonus
        
        # Normalize
        final_score = total_score / max(moment_count, 1)
        
        # Debug output
        if self.debug:
            print(f"    === Judge Analysis ===")
            for analysis in interval_analysis[:6]:
                offset = analysis['offset']
                beat = analysis['beat_strength']
                cons = analysis['consonances']
                diss = analysis['dissonances']
                unis = analysis['unisons']
                pairs = analysis['pairs']
                print(f"    Offset {offset} ({beat}): {cons}C, {diss}D, {unis}U of {pairs}")
                for p1, p2, interval, is_cons, is_unis in analysis['intervals']:
                    if is_unis:
                        status = "UNISON"
                    elif is_cons:
                        status = "CONS"
                    else:
                        status = "DISS"
                    print(f"      {p1} - {p2}: {interval} ({status})")
            if len(interval_analysis) > 6:
                print(f"    ... and {len(interval_analysis) - 6} more moments")
            print(f"    Strong beat consonance ratio: {strong_beat_consonances}/{strong_beat_moments}")
            
        return final_score

class SimplifiedCanonGenerator:
    """
    Generates optimal three-voice prolation canons with simplified entry timing.
    
    Voice 1: Original melody at normal speed
    Voice 2: Enters after Voice 1 completes, prolation factor p (2x, 3x, etc.)
    Voice 3: Enters after Voice 2 completes, prolation factor p² (4x, 9x, etc.)
    
    Searches both prolation factors and canon intervals for optimal consonance.
    """
    
    def __init__(self, melody_staff: abjad.Staff, time_signature: abjad.TimeSignature, 
                 key: str = "c major", min_prolation: int = 2, max_prolation: int = 5, 
                 search_intervals: List[int] = None, debug: bool = False, judge: Judge = None):
        """
        Initialize simplified canon generator.
        
        Args:
            melody_staff: Abjad Staff containing the melody
            time_signature: Time signature for the canon
            key: Key for diatonic transposition (e.g., "c major", "g major")
            min_prolation: Minimum prolation factor to search (default: 2)
            max_prolation: Maximum prolation factor to search (default: 5)
            search_intervals: List of canon intervals to search (default: [2,3,4,5,6,7])
            debug: If True, print verbose debugging information
            judge: Judge instance for scoring canons (if None, creates default)
        """
        self.melody_staff = melody_staff
        self.time_signature = time_signature
        self.key = key
        self.min_prolation = min_prolation
        self.max_prolation = max_prolation
        self.debug = debug
        
        # Set intervals to search (default: second through seventh, avoiding unison)
        if search_intervals is None:
            self.search_intervals = [3, 5, 6, 8]  # Second through seventh
        else:
            self.search_intervals = search_intervals
        
        # Use provided judge or create default
        if judge is None:
            default_rubric = Rubric()
            self.judge = Judge(default_rubric, time_signature, debug)
        else:
            self.judge = judge
        
        # Parse the key to get the scale
        self.scale_pitches = self._get_scale_pitches(key)
        
        # Calculate original melody duration
        self.original_melody_duration = sum(note.written_duration() 
                                          for note in self.extract_melody_notes())
        
    def _get_scale_pitches(self, key: str) -> List[abjad.NamedPitchClass]:
        """Get the pitch classes for a given key."""
        parts = key.lower().split()
        tonic = parts[0]
        mode = parts[1] if len(parts) > 1 else "major"
        
        scale_patterns = {
            "major": [0, 2, 4, 5, 7, 9, 11],
            "minor": [0, 2, 3, 5, 7, 8, 10]
        }
        
        if mode not in scale_patterns:
            mode = "major"
            
        tonic_pitch = abjad.NamedPitchClass(tonic)
        tonic_number = tonic_pitch.number()
        
        scale = []
        for interval in scale_patterns[mode]:
            pitch_number = (tonic_number + interval) % 12
            pitch_class = abjad.NamedPitchClass(pitch_number)
            scale.append(pitch_class)
            
        return scale
    
    def transpose_pitch_by_scale_degrees(self, pitch: abjad.NamedPitch, scale_degrees: int) -> abjad.NamedPitch:
        """
        Transpose a pitch down by the specified number of diatonic scale degrees.
        """
        try:
            # Get the current pitch class
            current_pc = pitch.pitch_class()
            current_pc_name = current_pc.name()
            
            # Find the current position in the scale
            scale_names = [pc.name() for pc in self.scale_pitches]
            if current_pc_name not in scale_names:
                # Find closest scale degree
                current_number = current_pc.number()
                closest_pc = min(self.scale_pitches, 
                               key=lambda pc: min(abs(pc.number() - current_number),
                                                 abs(pc.number() - current_number + 12),
                                                 abs(pc.number() - current_number - 12)))
                current_scale_index = scale_names.index(closest_pc.name())
            else:
                current_scale_index = scale_names.index(current_pc_name)
            
            # Calculate new scale position (wrapping around)
            new_scale_index = (current_scale_index - scale_degrees) % len(self.scale_pitches)
            new_pc = self.scale_pitches[new_scale_index]
            
            # Calculate octave adjustment
            octave_adjustment = 0
            if scale_degrees > 0 and new_scale_index > current_scale_index:
                octave_adjustment = -1
            
            # Get the original pitch's octave information
            original_name = str(pitch)
            apostrophes = original_name.count("'")
            commas = original_name.count(",")
            
            # Calculate new octave
            if apostrophes > 0:
                new_octave_apostrophes = max(0, apostrophes + octave_adjustment)
                new_commas = 0
            elif commas > 0:
                new_commas = max(0, commas - octave_adjustment)
                new_octave_apostrophes = 0
            else:
                if octave_adjustment > 0:
                    new_octave_apostrophes = octave_adjustment
                    new_commas = 0
                elif octave_adjustment < 0:
                    new_commas = -octave_adjustment
                    new_octave_apostrophes = 0
                else:
                    new_octave_apostrophes = 0
                    new_commas = 0
            
            # Build new pitch name
            new_pitch_name = new_pc.name()
            if new_octave_apostrophes > 0:
                new_pitch_name += "'" * new_octave_apostrophes
            elif new_commas > 0:
                new_pitch_name += "," * new_commas
            
            return abjad.NamedPitch(new_pitch_name)
                
        except Exception as e:
            if self.debug:
                print(f"Transposition error: {e}")
            return pitch
    
    def extract_melody_notes(self) -> List[abjad.Note]:
        """Extract all notes from the melody staff."""
        return [leaf for leaf in abjad.iterate.leaves(self.melody_staff) 
                if isinstance(leaf, abjad.Note)]
    
    def copy_melody_notes(self) -> List[abjad.Note]:
        """Create fresh copies of melody notes to avoid parent conflicts."""
        melody_notes = self.extract_melody_notes()
        return [abjad.Note(note.written_pitch(), note.written_duration()) 
                for note in melody_notes]
    
    def create_prolated_voice(self, prolation_factor: int, voice_number: int, 
                            entry_delay: Fraction, canon_interval: int = 1) -> abjad.Staff:
        """
        Create a voice with prolated durations and diatonic transposition.
        Voices repeat their melodies to fill the entire remaining duration after entry.
        
        Args:
            prolation_factor: Factor to multiply durations by for the entire canon
            voice_number: Voice number (1, 2, or 3)
            entry_delay: How long to wait before entering
            canon_interval: Scale degree interval for this canon (1=unison, 2=second, etc.)
            
        Returns:
            Abjad Staff with the prolated and transposed voice
        """
        components = []
        
        # Add rests for entry delay
        if entry_delay > 0:
            remaining_delay = entry_delay
            while remaining_delay > 0:
                if remaining_delay >= 1:
                    components.append(abjad.Rest('r1'))
                    remaining_delay -= 1
                elif remaining_delay >= Fraction(1, 2):
                    components.append(abjad.Rest('r2'))
                    remaining_delay -= Fraction(1, 2)
                elif remaining_delay >= Fraction(1, 4):
                    components.append(abjad.Rest('r4'))
                    remaining_delay -= Fraction(1, 4)
                else:
                    components.append(abjad.Rest('r8'))
                    remaining_delay -= Fraction(1, 8)
        
        # Calculate total piece duration (when voice 3 finishes)
        # Voice 3 starts at: original_duration + original_duration * prolation_factor
        # Voice 3 duration: original_duration * prolation_factor^2
        total_duration = (self.original_melody_duration + 
                         self.original_melody_duration * prolation_factor + 
                         self.original_melody_duration * (prolation_factor ** 2))
        
        # Calculate how long this voice needs to play after entry
        remaining_duration = total_duration - entry_delay
        
        # Calculate this voice's prolation
        if voice_number == 1:
            voice_prolation = 1
        elif voice_number == 2:
            voice_prolation = prolation_factor
        else:  # voice_number == 3
            voice_prolation = prolation_factor ** 2
        
        # Calculate how many repetitions needed to fill the remaining duration
        single_statement_duration = self.original_melody_duration * voice_prolation
        repetitions_needed = int(remaining_duration / single_statement_duration) + 1
        
        if self.debug:
            print(f"  Voice {voice_number}: {repetitions_needed} repetitions, {voice_prolation}x prolation")
            print(f"    Entry delay: {entry_delay}, Remaining duration: {remaining_duration}")
            print(f"    Single statement duration: {single_statement_duration}")
        
        # Copy and transform melody notes for each repetition
        melody_notes = self.copy_melody_notes()
        
        # Calculate measure duration for splitting long notes
        measure_duration = Fraction(self.time_signature.numerator, self.time_signature.denominator)
        max_duration = measure_duration  # Split anything longer than 1 measure
        
        # Create notes one repetition at a time
        for rep in range(repetitions_needed):
            # Collect pitches and durations for this single repetition
            rep_pitches = []
            rep_durations = []
            
            for note in melody_notes:
                # Apply prolation to duration  
                new_duration = note.written_duration() * voice_prolation
                
                # Apply diatonic transposition based on voice number and canon interval
                new_pitch = note.written_pitch()
                if voice_number == 2:
                    # Voice 2: transpose down by (canon_interval - 1) scale degrees
                    scale_degrees_down = canon_interval - 1
                    new_pitch = self.transpose_pitch_by_scale_degrees(new_pitch, scale_degrees_down)
                elif voice_number == 3:
                    # Voice 3: transpose down by 2 * (canon_interval - 1) scale degrees
                    scale_degrees_down = 2 * (canon_interval - 1)
                    new_pitch = self.transpose_pitch_by_scale_degrees(new_pitch, scale_degrees_down)
                
                # Split long durations before passing to make_notes
                if new_duration <= max_duration:
                    # Duration is manageable
                    rep_pitches.append(new_pitch)
                    rep_durations.append(abjad.Duration(new_duration))
                else:
                    # Duration is too long, split into measure-length chunks
                    remaining_duration = new_duration
                    while remaining_duration > 0:
                        chunk_duration = min(remaining_duration, max_duration)
                        rep_pitches.append(new_pitch)
                        rep_durations.append(abjad.Duration(chunk_duration))
                        remaining_duration -= chunk_duration
            
            # Now make_notes can handle all durations safely
            if rep_pitches and rep_durations:
                repetition_notes = abjad.makers.make_notes(rep_pitches, rep_durations)
                components.extend(repetition_notes)
        
        # Create staff
        staff_name = f"Voice {voice_number}"
        staff = abjad.Staff(components, name=staff_name)
        
        # Apply meter boundaries
        self.apply_meter_boundaries(staff)
        
        return staff
    
    def apply_meter_boundaries(self, staff: abjad.Staff) -> None:
        """Split notes at meter boundaries and add ties as needed."""
        # Use Abjad's meter to split notes at measure boundaries
        # Note: Time signature should be attached elsewhere, not here
        try:
            abjad.Meter.rewrite_meter(staff, self.time_signature)
        except Exception as e:
            if self.debug:
                print(f"Warning: Could not apply meter rewriting: {e}")
    
    def calculate_entry_delays(self, prolation_factor: int) -> Tuple[Fraction, Fraction, Fraction]:
        """
        Calculate entry delays for each voice based on the simplified timing scheme.
        
        Args:
            prolation_factor: The prolation factor being tested
            
        Returns:
            Tuple of (voice1_delay, voice2_delay, voice3_delay)
        """
        # Voice 1: starts immediately
        voice1_delay = Fraction(0)
        
        # Voice 2: enters after Voice 1 completes one full statement
        voice2_delay = self.original_melody_duration
        
        # Voice 3: enters after Voice 2 completes one full statement
        # Voice 2's duration is original_duration * prolation_factor
        voice3_delay = voice2_delay + (self.original_melody_duration * prolation_factor)
        
        return voice1_delay, voice2_delay, voice3_delay
    
    def find_optimal_canon(self) -> Tuple[abjad.Score, int, int, float]:
        """
        Search for the optimal prolation factor and canon interval combination.
        
        Returns:
            Tuple of (best_score, best_prolation_factor, best_canon_interval, best_score_value)
        """
        best_score = float('-inf')
        best_prolation_factor = self.min_prolation
        best_canon_interval = 1
        best_canon_score = None
        
        total_combinations = (self.max_prolation - self.min_prolation + 1) * len(self.search_intervals)
        print(f"Searching {self.max_prolation - self.min_prolation + 1} prolation factors × {len(self.search_intervals)} canon intervals = {total_combinations} combinations...")
        print("Prolation | Canon Interval | Voice 2 Timing | Voice 3 Timing | Consonance Score")
        print("-" * 80)
        
        for prolation in range(self.min_prolation, self.max_prolation + 1):
            for canon_interval in self.search_intervals:
                # Calculate entry delays for this prolation
                v1_delay, v2_delay, v3_delay = self.calculate_entry_delays(prolation)
                
                if self.debug:
                    print(f"\nTesting prolation {prolation}, canon interval {canon_interval}:")
                    print(f"  Voice 1: delay={v1_delay}, prolation=1x, no transposition")
                    print(f"  Voice 2: delay={v2_delay}, prolation={prolation}x, down {canon_interval-1} degrees")
                    print(f"  Voice 3: delay={v3_delay}, prolation={prolation**2}x, down {2*(canon_interval-1)} degrees")
                
                # Create voices with this prolation and canon interval
                voice1 = self.create_prolated_voice(1, 1, v1_delay, canon_interval)
                voice2 = self.create_prolated_voice(prolation, 2, v2_delay, canon_interval)
                voice3 = self.create_prolated_voice(prolation**2, 3, v3_delay, canon_interval)
                
                # Create temporary score and evaluate
                temp_score = abjad.Score([voice1, voice2, voice3])
                score = self.judge.evaluate_score(temp_score)
                
                # Display results
                interval_name = self._get_interval_name(canon_interval)
                print(f"{prolation:>9} | {interval_name:>13} | {str(v2_delay):>13} | {str(v3_delay):>13} | {score:>15.3f}")
                
                # Track best score
                if score > best_score:
                    best_score = score
                    best_prolation_factor = prolation
                    best_canon_interval = canon_interval
                    best_canon_score = temp_score
                    print(f"                                                                      ^^^ NEW BEST! ^^^")
        
        return best_canon_score, best_prolation_factor, best_canon_interval, best_score
    
    def _get_interval_name(self, canon_interval: int) -> str:
        """Convert canon interval number to name."""
        interval_names = {
            1: "Unison", 2: "Second", 3: "Third", 4: "Fourth", 
            5: "Fifth", 6: "Sixth", 7: "Seventh", 8: "Octave"
        }
        return interval_names.get(canon_interval, f"{canon_interval}th")
    
    def generate_canon(self) -> abjad.Score:
        """
        Generate the optimal prolation canon.
        
        Returns:
            Abjad Score with the optimal three-voice prolation canon
        """
        # Find optimal prolation and canon interval
        best_score, best_prolation, best_canon_interval, best_score_value = self.find_optimal_canon()
        
        if best_score is None:
            print("No valid canon configuration found!")
            return None
        
        # Display optimal configuration
        v1_delay, v2_delay, v3_delay = self.calculate_entry_delays(best_prolation)
        interval_name = self._get_interval_name(best_canon_interval)
        
        print(f"\nOptimal prolation canon found:")
        print(f"Prolation factor: {best_prolation}")
        print(f"Canon interval: {interval_name} (interval {best_canon_interval})")
        print(f"Voice 1: Original melody, starts immediately, no transposition")
        print(f"Voice 2: {best_prolation}x durations, enters at {v2_delay}, transposed down {best_canon_interval-1} scale degrees")
        print(f"Voice 3: {best_prolation**2}x durations, enters at {v3_delay}, transposed down {2*(best_canon_interval-1)} scale degrees")
        print(f"Key: {self.key}")
        print(f"Consonance score: {best_score_value:.3f}")
        
        # Create final score with proper formatting
        voice1 = self.create_prolated_voice(1, 1, v1_delay, best_canon_interval)
        voice2 = self.create_prolated_voice(best_prolation, 2, v2_delay, best_canon_interval)
        voice3 = self.create_prolated_voice(best_prolation**2, 3, v3_delay, best_canon_interval)
        
        # Set appropriate clefs and time signature
        abjad.attach(abjad.Clef('treble'), voice1[0])
        abjad.attach(abjad.Clef('treble'), voice2[0])
        abjad.attach(abjad.Clef('bass'), voice3[0])
        
        # Attach time signature only to the very first note of the score
        first_leaf = abjad.get.leaf(voice1, 0)
        abjad.attach(self.time_signature, first_leaf)
        
        # Create final score
        final_score = abjad.Score([voice1, voice2, voice3], name="Three-Voice Prolation Canon")
        
        return final_score

def save_score_to_file(score: abjad.Score, filename: str = "simplified_canon.ly") -> str:
    """Save an Abjad score to a LilyPond file with proper headers."""
    import os
    
    if not filename.endswith('.ly'):
        filename += '.ly'
    
    output_path = os.path.join(os.getcwd(), filename)
    
    lilypond_content = f'''\\version "2.24.0"
\\language "english"

\\header {{
  title = "Three-Voice Prolation Canon"
  subtitle = "Generated by Simplified Canon Generator"
  composer = "Abjad"
}}

{abjad.lilypond(score)}
'''
    
    with open(output_path, 'w') as f:
        f.write(lilypond_content)
    
    return output_path

def create_sample_melody() -> abjad.Staff:
    """Create the traditional Korean folk song Arirang."""
    # Traditional Korean folk song Arirang - beautiful melody perfect for canon testing
    arirang_lilypond = "e'4.( fs'8 e'4 a'4. b'8 a' b' cs''4 b'8 cs''16 b' a'8 fs' e'4.) fs'8( e' fs' a'4. b'8 a' b' cs'' b' a' fs' e' fs' a'4. b'8 a'4 a'2.) e''2( e''4 e'' cs'' b' cs'' b'8 cs''16 b' a'8 fs' e'4.) fs'8( e' fs' a'4. b'8 a' b' cs'' b' a' fs' e' fs' a'4. b'8 a'4 a'2.)"
    
    melody = abjad.Staff(arirang_lilypond)
    print("Sample melody (Traditional Korean folk song - Arirang):")
    note_count = 0
    for leaf in abjad.iterate.leaves(melody):
        if isinstance(leaf, abjad.Note):
            note_count += 1
            if note_count <= 10:  # Show first 10 notes
                print(f"  Note {note_count}: {leaf.written_pitch()} - {leaf.written_duration()}")
    
    if note_count > 10:
        print(f"  ... and {note_count - 10} more notes")
    
    print(f"Total melody duration: {sum(note.written_duration() for note in abjad.iterate.leaves(melody) if isinstance(note, abjad.Note))}")
    return melody

# Example usage
if __name__ == "__main__":
    # Create sample inputs
    melody_staff = create_sample_melody()
    time_signature = abjad.TimeSignature((3, 4))  # Arirang is in 3/4 time
    
    # Create a custom rubric
    custom_rubric = Rubric(
        strong_beat_consonance=5.0,
        medium_beat_consonance=2.0, 
        weak_beat_consonance=1.0,
        strong_beat_unison_penalty=-3.0,
        medium_beat_unison_penalty=-1.5,
        weak_beat_unison_penalty=-0.5,
        strong_beat_dissonance_penalty=-2.0,
        medium_beat_dissonance_penalty=-0.5,
        weak_beat_dissonance_penalty=0.0,
        overall_consonance_bonus=10.0
    )
    
    # Create judge with custom rubric (no beat_template needed - uses Abjad's Meter)
    judge = Judge(rubric=custom_rubric, time_signature=time_signature, debug=False)
    
    # Generate simplified canon
    generator = SimplifiedCanonGenerator(
        melody_staff, 
        time_signature,
        key="c major",
        min_prolation=2,
        max_prolation=4,  # Search prolation factors 2, 3, 4
        search_intervals=[2, 3, 4, 5, 6],  # Skip unison and 7th (avoid unison, 7th often dissonant)
        debug=False,
        judge=judge
    )
    
    canon_score = generator.generate_canon()
    
    if canon_score:
        # Display the result
        print("\nGenerated LilyPond:")
        print(abjad.lilypond(canon_score))
        
        # Save to file
        output_file = save_score_to_file(canon_score, "simplified_prolation_canon.ly")
        print(f"\nScore saved to: {output_file}")
    else:
        print("Failed to generate canon.")