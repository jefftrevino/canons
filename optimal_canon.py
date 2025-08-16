import abjad
from fractions import Fraction
from typing import List, Tuple, Dict, Optional
import itertools

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
        
        Args:
            strong_beat_consonance: Points for consonant intervals on strong beats
            medium_beat_consonance: Points for consonant intervals on medium beats
            weak_beat_consonance: Points for consonant intervals on weak beats
            strong_beat_unison_penalty: Penalty for unisons on strong beats
            medium_beat_unison_penalty: Penalty for unisons on medium beats
            weak_beat_unison_penalty: Penalty for unisons on weak beats
            strong_beat_dissonance_penalty: Penalty for dissonance on strong beats
            medium_beat_dissonance_penalty: Penalty for dissonance on medium beats
            weak_beat_dissonance_penalty: Penalty for dissonance on weak beats
            overall_consonance_bonus: Bonus multiplier for overall consonance ratio
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
    
    def __init__(self, rubric: Rubric, beat_template: List[str], time_signature: abjad.TimeSignature, debug: bool = False):
        """
        Initialize judge with scoring rubric.
        
        Args:
            rubric: Rubric defining scoring criteria
            beat_template: Beat strength template ['S', 'w', 'm', 'w']
            time_signature: Time signature for beat strength calculation
            debug: If True, print detailed analysis
        """
        self.rubric = rubric
        self.beat_template = beat_template
        self.time_signature = time_signature
        self.debug = debug
        
        # Define consonant intervals
        self.consonant_intervals = {
            'P1', 'P8', 'P5', 'P4',  # Perfect consonances
            'M3', 'm3', 'M6', 'm6'   # Imperfect consonances
        }
        
        self.consonant_interval_classes = {
            0, 7, 5, 4, 3, 8, 9  # Semitone classes
        }
    
    def get_beat_strength(self, offset: Fraction) -> str:
        """Determine beat strength at given offset."""
        beats_per_measure = self.time_signature.numerator
        beat_duration = Fraction(1, self.time_signature.denominator)
        
        position_in_measure = offset % (beats_per_measure * beat_duration)
        beat_number = int(position_in_measure / beat_duration)
        
        template_index = beat_number % len(self.beat_template)
        return self.beat_template[template_index]
    
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
        
        Args:
            score: Abjad Score to evaluate
            
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
    def apply_meter_boundaries(self, staff: abjad.Staff) -> None:
        """
        Split notes at meter boundaries and add ties as needed.
        """
        # First, ensure we have a time signature attached
        time_sig_found = False
        for leaf in abjad.iterate.leaves(staff):
            indicators = abjad.get.indicators(leaf, abjad.TimeSignature)
            if indicators:
                time_sig_found = True
                break
        
        if not time_sig_found and len(staff) > 0:
            # Attach time signature to first leaf if not present
            abjad.attach(self.time_signature, staff[0])
        
        # Use Abjad's meter to split notes at measure boundaries
        try:
            # Apply meter to the staff - this splits long notes at barlines
            abjad.Meter.rewrite_meter(staff, self.time_signature)
        except Exception as e:
            if self.debug:
                print(f"    Warning: Could not apply meter rewriting: {e}")
            # Fallback: manually split long durations if automatic rewriting fails
            self._manual_meter_split(staff)
    
    def _manual_meter_split(self, staff: abjad.Staff) -> None:
        """
        Manually split notes that cross barlines - fallback method.
        """
        measure_duration = Fraction(self.time_signature.numerator, self.time_signature.denominator)
        current_position = Fraction(0)
        
        # Convert staff to a list to allow modification during iteration
        leaves = list(abjad.iterate.leaves(staff))
        
        for leaf in leaves:
            if isinstance(leaf, abjad.Note):
                note_duration = leaf.written_duration()
                note_end = current_position + note_duration
                
                # Check if note crosses a barline
                current_measure_end = ((current_position // measure_duration) + 1) * measure_duration
                
                if note_end > current_measure_end and current_position < current_measure_end:
                    # Note crosses barline, needs to be split
                    try:
                        # Duration before barline
                        first_duration = current_measure_end - current_position
                        # Duration after barline  
                        second_duration = note_end - current_measure_end
                        
                        if first_duration > 0 and second_duration > 0:
                            # Create two tied notes
                            first_note = abjad.Note(leaf.written_pitch(), first_duration)
                            second_note = abjad.Note(leaf.written_pitch(), second_duration)
                            
                            # Add tie
                            abjad.tie([first_note, second_note])
                            
                            # Replace the original note
                            leaf_index = staff.index(leaf)
                            staff.pop(leaf_index)
                            staff.insert(leaf_index, first_note)
                            staff.insert(leaf_index + 1, second_note)
                    except:
                        # If splitting fails, leave the note as is
                        pass
            
            current_position += leaf.written_duration()
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

class CanonGenerator:
    """
    Generates optimal three-voice canons at the octave using Abjad.
    Uses search algorithm to find best entry points for maximum consonance on strong beats.
    """
    
    def __init__(self, melody_staff: abjad.Staff, time_signature: abjad.TimeSignature, 
                 beat_template: List[str], key: str = "c major",
                 max_entry_delay_measures: int = 2, debug: bool = False, 
                 add_analysis_markup: bool = False, judge: Judge = None,
                 search_intervals: List[int] = None, entry_resolution: str = "beat",
                 search_prolations: List[int] = None):
        """
        Initialize canon generator.
        
        Args:
            melody_staff: Abjad Staff containing the melody (voice 1)
            time_signature: Time signature for the canon
            beat_template: List of beat strengths ['S', 'w', 'm', 'w'] etc.
            key: Key for diatonic transposition (e.g., "c major", "g major")
            max_entry_delay_measures: Maximum delay in measures for voices 2 and 3
            debug: If True, print verbose debugging information
            add_analysis_markup: If True, add interval and consonance markup to the score
            judge: Judge instance for scoring canons (if None, creates default)
            search_intervals: List of canon intervals to search (if None, searches 1-7)
            entry_resolution: Entry timing resolution - "beat", "downbeat", "strong_beat", "half_beat", "quarter_beat"
            search_prolations: List of prolation values to search (if None, searches [1, 2])
        """
        self.melody_staff = melody_staff
        self.time_signature = time_signature
        self.beat_template = beat_template
        self.key = key
        self.max_entry_delay = max_entry_delay_measures
        self.debug = debug
        self.add_analysis_markup = add_analysis_markup
        self.entry_resolution = entry_resolution
        
        # Use provided judge or create default
        if judge is None:
            default_rubric = Rubric()
            self.judge = Judge(default_rubric, beat_template, time_signature, debug)
        else:
            self.judge = judge
        
        # Set intervals to search (default: unison through seventh)
        if search_intervals is None:
            self.search_intervals = [1, 2, 3, 4, 5, 6, 7]  # Unison through seventh
        else:
            self.search_intervals = search_intervals
        
        # Set prolations to search (default: normal and double time)
        if search_prolations is None:
            self.search_prolations = [1, 2]  # Normal and augmentation
        else:
            self.search_prolations = search_prolations
        
        # Parse the key to get the scale
        self.scale_pitches = self._get_scale_pitches(key)
        
    def _get_scale_pitches(self, key: str) -> List[abjad.NamedPitchClass]:
        """
        Get the pitch classes for a given key.
        
        Args:
            key: Key signature like "c major", "g major", "a minor"
            
        Returns:
            List of pitch classes in the scale
        """
        # Parse key string
        parts = key.lower().split()
        tonic = parts[0]
        mode = parts[1] if len(parts) > 1 else "major"
        
        # Define scale patterns (in semitones)
        scale_patterns = {
            "major": [0, 2, 4, 5, 7, 9, 11],
            "minor": [0, 2, 3, 5, 7, 8, 10]
        }
        
        if mode not in scale_patterns:
            mode = "major"  # Default fallback
            
        # Get tonic pitch class number
        tonic_pitch = abjad.NamedPitchClass(tonic)
        tonic_number = tonic_pitch.number()
        
        # Build scale
        scale = []
        for interval in scale_patterns[mode]:
            pitch_number = (tonic_number + interval) % 12
            pitch_class = abjad.NamedPitchClass(pitch_number)
            scale.append(pitch_class)
            
        return scale
    
    def transpose_pitch_by_scale_degrees(self, pitch: abjad.NamedPitch, scale_degrees: int) -> abjad.NamedPitch:
        """
        Transpose a pitch down by the specified number of diatonic scale degrees.
        
        Args:
            pitch: Original pitch
            scale_degrees: Number of scale degrees to transpose down (0=unison, 1=down one degree, etc.)
            
        Returns:
            Transposed pitch within the key
        """
        try:
            if self.debug:
                print(f"  Transposing {pitch} down by {scale_degrees} scale degrees")
                print(f"  Scale: {[pc.name() for pc in self.scale_pitches]}")
            
            # Get the current pitch class
            current_pc = pitch.pitch_class()
            current_pc_name = current_pc.name()
            
            # Find the current position in the scale
            scale_names = [pc.name() for pc in self.scale_pitches]
            if current_pc_name not in scale_names:
                if self.debug:
                    print(f"  Warning: {current_pc_name} not in scale, using closest match")
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
            # If we wrapped around the scale going down, we need to go down an octave
            octave_adjustment = 0
            if scale_degrees > 0 and new_scale_index > current_scale_index:
                octave_adjustment = -1
            
            # Get the original pitch's octave information
            original_name = str(pitch)
            apostrophes = original_name.count("'")
            commas = original_name.count(",")
            
            # Calculate new octave
            if apostrophes > 0:
                # Pitch is above middle C
                new_octave_apostrophes = max(0, apostrophes + octave_adjustment)
                new_commas = 0
            elif commas > 0:
                # Pitch is below middle C
                new_commas = max(0, commas - octave_adjustment)
                new_octave_apostrophes = 0
            else:
                # Pitch is around middle C
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
            
            new_pitch = abjad.NamedPitch(new_pitch_name)
            
            if self.debug:
                print(f"  Result: {new_pitch}")
            
            return new_pitch
                
        except Exception as e:
            if self.debug:
                print(f"Transposition error: {e}")
                import traceback
                traceback.print_exc()
            print(f"Scale degree transposition error for {pitch}, returning original")
            return pitch
    
    def extract_melody_notes(self) -> List[abjad.Note]:
        """Extract all notes from the melody staff."""
        return [leaf for leaf in abjad.iterate.leaves(self.melody_staff) 
                if isinstance(leaf, abjad.Note)]
    
    def get_beat_strength(self, offset: Fraction) -> str:
        """
        Determine beat strength at given offset based on template.
        
        Args:
            offset: Musical offset (in fractions of a whole note)
            
        Returns:
            Beat strength: 'S' (strong), 'm' (medium), 'w' (weak)
        """
        beats_per_measure = self.time_signature.numerator
        beat_duration = Fraction(1, self.time_signature.denominator)
        
        # Calculate position within measure
        position_in_measure = offset % (beats_per_measure * beat_duration)
        beat_number = int(position_in_measure / beat_duration)
        
        # Use template cyclically if needed
        template_index = beat_number % len(self.beat_template)
        return self.beat_template[template_index]
        """
        Determine beat strength at given offset based on template.
        
        Args:
            offset: Musical offset (in fractions of a whole note)
            
        Returns:
            Beat strength: 'S' (strong), 'm' (medium), 'w' (weak)
        """
        beats_per_measure = self.time_signature.numerator
        beat_duration = Fraction(1, self.time_signature.denominator)
        
        # Calculate position within measure
        position_in_measure = offset % (beats_per_measure * beat_duration)
        beat_number = int(position_in_measure / beat_duration)
        
        # Use template cyclically if needed
        template_index = beat_number % len(self.beat_template)
        return self.beat_template[template_index]
    
    def calculate_interval(self, pitch1: abjad.NamedPitch, pitch2: abjad.NamedPitch) -> str:
        """Calculate the interval between two pitches."""
        try:
            interval = abjad.NamedInterval.from_pitch_carriers(pitch1, pitch2)
            return interval.name()
        except:
            # Fallback: use semitone calculation
            semitones = abs(pitch1.number() - pitch2.number()) % 12
            interval_map = {
                0: 'P1', 1: 'm2', 2: 'M2', 3: 'm3', 4: 'M3', 5: 'P4',
                6: 'TT', 7: 'P5', 8: 'm6', 9: 'M6', 10: 'm7', 11: 'M7'
            }
            return interval_map.get(semitones, 'unknown')
    
    def is_consonant(self, interval_name: str) -> bool:
        """Check if an interval is consonant."""
        # Primary check
        if interval_name in self.consonant_intervals:
            return True
            
        # Fallback: check by semitone class for compound intervals
        semitone_map = {
            'P1': 0, 'm2': 1, 'M2': 2, 'm3': 3, 'M3': 4, 'P4': 5,
            'TT': 6, 'P5': 7, 'm6': 8, 'M6': 9, 'm7': 10, 'M7': 11
        }
        
        if interval_name in semitone_map:
            semitones = semitone_map[interval_name]
            return semitones in self.consonant_interval_classes
            
        return False
    
    def create_canon_voice(self, melody_notes: List[abjad.Note], 
                          entry_delay: Fraction, voice_number: int = 1, 
                          voice_name: str = None, max_delay_used: Fraction = None,
                          canon_interval: int = 1, prolation: int = 1) -> abjad.Staff:
        """
        Create a canon voice with specified entry delay, interval transposition, and prolation.
        
        Args:
            melody_notes: List of melody notes
            entry_delay: Delay before voice enters (in whole note fractions)
            voice_number: Which voice this is (1=original, 2=first transposition, 3=second transposition)
            voice_name: Name for the staff
            max_delay_used: The actual maximum delay being used in this canon
            canon_interval: Scale degree interval for this canon
            prolation: Duration multiplier for this voice (1=normal, 2=double, etc.)
            
        Returns:
            Abjad Staff containing the canon voice
        """
        components = []
        
        # Calculate total duration needed with prolation considerations
        melody_duration = sum(note.written_duration() for note in melody_notes)
        
        if max_delay_used is not None:
            # For prolation canons, we need to account for the longest voice duration
            # Voice 3 with prolation^2 will take the longest
            max_prolation_multiplier = prolation ** (voice_number - 1)
            total_duration_needed = max_delay_used + (melody_duration * max_prolation_multiplier)
        else:
            # Fallback: use current voice's requirement
            voice_prolation_multiplier = prolation ** (voice_number - 1)
            total_duration_needed = entry_delay + (melody_duration * voice_prolation_multiplier)
        
        if self.debug:
            voice_prolation = prolation ** (voice_number - 1)
            print(f"  Voice {voice_number}: prolation={voice_prolation}x, entry_delay={entry_delay}, total_needed={total_duration_needed}")
        
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
        
        # Calculate how much music we need after the entry delay
        remaining_duration = total_duration_needed - entry_delay
        current_duration = Fraction(0)
        
        if self.debug:
            print(f"  Voice {voice_number}: needs {remaining_duration} duration of music")
        
        # Add melody notes with prolation, repeating as necessary
        repetition_count = 0
        voice_prolation_multiplier = prolation ** (voice_number - 1)
        
        while current_duration < remaining_duration:
            repetition_count += 1
            if self.debug and repetition_count > 1:
                print(f"  Voice {voice_number}: starting repetition {repetition_count}")
            
            # Collect pitches and durations for this repetition
            pitches = []
            durations = []
            
            for note in melody_notes:
                if current_duration >= remaining_duration:
                    break
                    
                original_pitch = note.written_pitch()
                new_pitch = original_pitch
                
                # Apply scale degree transpositions based on voice number
                if voice_number == 2:
                    scale_degrees_down = canon_interval - 1
                    new_pitch = self.transpose_pitch_by_scale_degrees(original_pitch, scale_degrees_down)
                elif voice_number == 3:
                    scale_degrees_down = 2 * (canon_interval - 1)
                    new_pitch = self.transpose_pitch_by_scale_degrees(original_pitch, scale_degrees_down)
                
                # Apply prolation to duration
                original_duration = note.written_duration()
                prolated_duration = original_duration * voice_prolation_multiplier
                
                pitches.append(new_pitch)
                durations.append(prolated_duration)
                current_duration += prolated_duration
            
            # Use make_notes to handle complex durations properly
            if pitches and durations:
                new_notes = abjad.makers.make_notes(pitches, durations)
                components.extend(new_notes)
        
        if self.debug:
            print(f"  Voice {voice_number}: created {repetition_count} repetitions with {voice_prolation_multiplier}x prolation")
        
        # Create staff with name during construction
        staff = abjad.Staff(components, name=voice_name)
        
        # Apply meter boundaries to split notes at barlines
        self.apply_meter_boundaries(staff)
        
        return staff
    
    def evaluate_canon_score(self, voice1_staff: abjad.Staff, voice2_staff: abjad.Staff, 
                           voice3_staff: abjad.Staff) -> float:
        """
        Evaluate the quality of a three-voice canon based on consonance on strong beats.
        
        Returns:
            Score (higher is better): weighted sum of consonances on strong/medium/weak beats
        """
        # Create temporary score for analysis
        score = abjad.Score([voice1_staff, voice2_staff, voice3_staff])
        
        total_score = 0.0
        moment_count = 0
        strong_beat_consonances = 0
        strong_beat_moments = 0
        interval_analysis = []
        
        # Analyze each vertical moment
        for moment in abjad.iterate_vertical_moments(score):
            leaves = moment.leaves()
            if len(leaves) < 2:
                continue
                
            moment_count += 1
            beat_strength = self.get_beat_strength(moment.offset())
            
            # Calculate all pairwise intervals at this moment
            moment_consonances = 0
            moment_pairs = 0
            moment_intervals = []
            
            for i, leaf1 in enumerate(leaves):
                for leaf2 in leaves[i+1:]:
                    if isinstance(leaf1, abjad.Note) and isinstance(leaf2, abjad.Note):
                        interval = self.calculate_interval(leaf1.written_pitch(), 
                                                         leaf2.written_pitch())
                        moment_pairs += 1
                        is_cons = self.is_consonant(interval)
                        moment_intervals.append((leaf1.written_pitch(), leaf2.written_pitch(), interval, is_cons))
                        
                        if is_cons:
                            moment_consonances += 1
            
            # Store analysis for debugging
            interval_analysis.append({
                'offset': moment.offset(),
                'beat_strength': beat_strength,
                'intervals': moment_intervals,
                'consonances': moment_consonances,
                'pairs': moment_pairs
            })
            
            # Weight consonances based on beat strength
            if moment_pairs > 0:
                consonance_ratio = moment_consonances / moment_pairs
                
                if beat_strength == 'S':
                    total_score += consonance_ratio * 5.0  # Strong beats weighted very heavily
                    strong_beat_consonances += moment_consonances
                    strong_beat_moments += moment_pairs
                elif beat_strength == 'm':
                    total_score += consonance_ratio * 2.0  # Medium beats moderately weighted
                else:  # weak beats
                    total_score += consonance_ratio * 1.0  # Weak beats now counted positively
        
        # Add bonus for overall strong beat consonance
        if strong_beat_moments > 0:
            strong_beat_ratio = strong_beat_consonances / strong_beat_moments
            total_score += strong_beat_ratio * 10.0  # Big bonus for strong beat consonance
        
        # Normalize by moment count
        final_score = total_score / max(moment_count, 1)
        
        # Debug output for interval analysis
        if self.debug:
            print(f"    === Interval Analysis ===")
            for analysis in interval_analysis[:6]:  # Show first 6 moments
                offset = analysis['offset']
                beat = analysis['beat_strength']
                intervals = analysis['intervals']
                cons = analysis['consonances']
                pairs = analysis['pairs']
                print(f"    Offset {offset} ({beat} beat): {cons}/{pairs} consonant")
                for p1, p2, interval, is_cons in intervals:
                    status = "CONS" if is_cons else "DISS"
                    print(f"      {p1} - {p2}: {interval} ({status})")
            if len(interval_analysis) > 6:
                print(f"    ... and {len(interval_analysis) - 6} more moments")
            print(f"    Strong beat consonance: {strong_beat_consonances}/{strong_beat_moments}")
            
        return final_score
    
    def generate_entry_delays(self) -> List[Fraction]:
        """Generate all possible entry delays based on the specified resolution."""
        delays = []
        beat_duration = Fraction(1, self.time_signature.denominator)
        max_delay_duration = self.max_entry_delay * self.time_signature.numerator * beat_duration
        
        if self.entry_resolution == "downbeat":
            # Only allow entries on measure boundaries (downbeats)
            measure_duration = self.time_signature.numerator * beat_duration
            current_delay = Fraction(0)
            while current_delay <= max_delay_duration:
                delays.append(current_delay)
                current_delay += measure_duration
                
        elif self.entry_resolution == "strong_beat":
            # Only allow entries on beats marked as 'S' in the beat template
            current_delay = Fraction(0)
            while current_delay <= max_delay_duration:
                # Check if this delay corresponds to a strong beat
                beat_strength = self.judge.get_beat_strength(current_delay)
                if beat_strength == 'S':
                    delays.append(current_delay)
                current_delay += beat_duration
                
        elif self.entry_resolution == "beat":
            # Allow entries on any beat boundary (default)
            current_delay = Fraction(0)
            while current_delay <= max_delay_duration:
                delays.append(current_delay)
                current_delay += beat_duration
                
        elif self.entry_resolution == "half_beat":
            # Allow entries on beat and half-beat boundaries
            half_beat_duration = beat_duration / 2
            current_delay = Fraction(0)
            while current_delay <= max_delay_duration:
                delays.append(current_delay)
                current_delay += half_beat_duration
                
        elif self.entry_resolution == "quarter_beat":
            # Allow entries on quarter-beat boundaries (finest resolution)
            quarter_beat_duration = beat_duration / 4
            current_delay = Fraction(0)
            while current_delay <= max_delay_duration:
                delays.append(current_delay)
                current_delay += quarter_beat_duration
        else:
            # Default to beat resolution if unknown option
            current_delay = Fraction(0)
            while current_delay <= max_delay_duration:
                delays.append(current_delay)
                current_delay += beat_duration
        
        return delays
    
    def add_analysis_markup_to_score(self, final_score: abjad.Score) -> None:
        """
        Add consonance analysis by coloring noteheads.
        
        Color scheme:
        - Green: Consonant on strong beat (good!)
        - Red: Dissonant on strong beat (bad!)
        - Blue: Consonant on medium/weak beat
        - Gray: Dissonant on medium/weak beat (acceptable)
        """
        if not self.add_analysis_markup:
            return
            
        # Analyze each vertical moment and color noteheads
        for moment in abjad.iterate_vertical_moments(final_score):
            leaves = moment.leaves()
            if len(leaves) < 2:
                continue
                
            beat_strength = self.judge.get_beat_strength(moment.offset())
            
            # Calculate consonance ratio for this moment
            consonance_count = 0
            total_intervals = 0
            
            for i, leaf1 in enumerate(leaves):
                for leaf2 in leaves[i+1:]:
                    if isinstance(leaf1, abjad.Note) and isinstance(leaf2, abjad.Note):
                        interval = self.judge.calculate_interval(leaf1.written_pitch(), 
                                                               leaf2.written_pitch())
                        is_cons = self.judge.is_consonant(interval)
                        total_intervals += 1
                        if is_cons:
                            consonance_count += 1
            
            # Determine color based on consonance and beat strength
            if total_intervals > 0:
                consonance_ratio = consonance_count / total_intervals
                is_mostly_consonant = consonance_ratio >= 0.5
                
                if beat_strength == 'S':
                    if is_mostly_consonant:
                        color = "#(rgb-color 0 0.7 0)"      # Good: consonant on strong beat
                    else:
                        color = "#(rgb-color 0.8 0 0)"        # Bad: dissonant on strong beat
                elif beat_strength == 'm':
                    if is_mostly_consonant:
                        color = "#(rgb-color 0 0 0.8)"       # Consonant on medium beat
                    else:
                        color = "#(rgb-color 0.5 0.5 0.5)"       # Dissonant on medium beat
                else:  # weak beat
                    if is_mostly_consonant:
                        color = "#(rgb-color 0 0 0.8)"       # Consonant on weak beat
                    else:
                        color = "#(rgb-color 0.5 0.5 0.5)"       # Dissonant on weak beat (fine)
                
                # Color all noteheads at this moment
                for leaf in leaves:
                    if isinstance(leaf, abjad.Note):
                        abjad.override(leaf).NoteHead.color = color
    def copy_melody_notes(self) -> List[abjad.Note]:
        """Create fresh copies of melody notes to avoid parent conflicts."""
        melody_notes = self.extract_melody_notes()
        return [abjad.Note(note.written_pitch(), note.written_duration()) 
                for note in melody_notes]
    
    def apply_meter_boundaries(self, staff: abjad.Staff) -> None:
        """
        Split notes at meter boundaries and add ties as needed.
        """
        # First, ensure we have a time signature attached
        time_sig_found = False
        for leaf in abjad.iterate.leaves(staff):
            indicators = abjad.get.indicators(leaf, abjad.TimeSignature)
            if indicators:
                time_sig_found = True
                break
        
        if not time_sig_found and len(staff) > 0:
            # Attach time signature to first leaf if not present
            abjad.attach(self.time_signature, staff[0])
        
        # Use Abjad's meter to split notes at measure boundaries
        try:
            # Apply meter to the staff - this splits long notes at barlines
            abjad.Meter.rewrite_meter(staff, self.time_signature)
        except Exception as e:
            if self.debug:
                print(f"    Warning: Could not apply meter rewriting: {e}")
            # Fallback: manually split long durations if automatic rewriting fails
            self._manual_meter_split(staff)
    
    def _manual_meter_split(self, staff: abjad.Staff) -> None:
        """
        Manually split notes that cross barlines - fallback method.
        """
        measure_duration = Fraction(self.time_signature.numerator, self.time_signature.denominator)
        current_position = Fraction(0)
        
        # Convert staff to a list to allow modification during iteration
        leaves = list(abjad.iterate.leaves(staff))
        
        for leaf in leaves:
            if isinstance(leaf, abjad.Note):
                note_duration = leaf.written_duration()
                note_end = current_position + note_duration
                
                # Check if note crosses a barline
                current_measure_end = ((current_position // measure_duration) + 1) * measure_duration
                
                if note_end > current_measure_end and current_position < current_measure_end:
                    # Note crosses barline, needs to be split
                    try:
                        # Duration before barline
                        first_duration = current_measure_end - current_position
                        # Duration after barline  
                        second_duration = note_end - current_measure_end
                        
                        if first_duration > 0 and second_duration > 0:
                            # Create two tied notes
                            first_note = abjad.Note(leaf.written_pitch(), first_duration)
                            second_note = abjad.Note(leaf.written_pitch(), second_duration)
                            
                            # Add tie
                            abjad.tie([first_note, second_note])
                            
                            # Replace the original note
                            leaf_index = staff.index(leaf)
                            staff.pop(leaf_index)
                            staff.insert(leaf_index, first_note)
                            staff.insert(leaf_index + 1, second_note)
                    except:
                        # If splitting fails, leave the note as is
                        pass
            
            current_position += leaf.written_duration()
        melody_notes = self.extract_melody_notes()
        return [abjad.Note(note.written_pitch(), note.written_duration()) 
                for note in melody_notes]
    
    def find_optimal_canon(self) -> abjad.Score:
        """
        Search for the optimal three-voice canon configuration.
        Tests all combinations of prolations, canon intervals, and entry delays.
        
        Returns:
            Abjad Score with optimally-spaced canon voices
        """
        possible_delays = self.generate_entry_delays()
        
        best_score = float('-inf')  # Start with negative infinity so any score will be better
        best_configuration = None
        
        total_configurations = len(self.search_prolations) * len(self.search_intervals) * len(possible_delays) ** 2
        print(f"Searching {len(self.search_prolations)} prolations × {len(self.search_intervals)} intervals × {len(possible_delays)}² delays = {total_configurations} configurations...")
        print(f"Prolation Canon Interval Voice 2 Delay Voice 3 Delay Consonance Score")
        print("-" * 80)
        
        # Search all combinations of prolations, canon intervals, and entry delays
        for prolation in self.search_prolations:
            for canon_interval in self.search_intervals:
                for delay2, delay3 in itertools.product(possible_delays, repeat=2):
                    # Skip identical delays (voices would be in unison)
                    if delay2 == delay3:
                        continue
                        
                    # Find the maximum delay for this configuration
                    max_delay_in_config = max(Fraction(0), delay2, delay3)
                        
                    # Create three canon voices with prolation, interval transpositions
                    voice1 = self.create_canon_voice(self.copy_melody_notes(), Fraction(0), 
                                                   voice_number=1, voice_name="Voice 1",
                                                   max_delay_used=max_delay_in_config,
                                                   canon_interval=canon_interval,
                                                   prolation=prolation)
                    voice2 = self.create_canon_voice(self.copy_melody_notes(), delay2, 
                                                   voice_number=2, voice_name="Voice 2",
                                                   max_delay_used=max_delay_in_config,
                                                   canon_interval=canon_interval,
                                                   prolation=prolation)
                    voice3 = self.create_canon_voice(self.copy_melody_notes(), delay3, 
                                                   voice_number=3, voice_name="Voice 3",
                                                   max_delay_used=max_delay_in_config,
                                                   canon_interval=canon_interval,
                                                   prolation=prolation)
                    
                    # Evaluate this configuration using the judge
                    temp_score = abjad.Score([voice1, voice2, voice3])
                    score = self.judge.evaluate_score(temp_score)
                    
                    # Print score for this configuration
                    print(f"{prolation:<9} {canon_interval:<13} {str(delay2):<12} {str(delay3):<12} {score:<16.3f}")
                    
                    if score > best_score:
                        best_score = score
                        best_configuration = (prolation, canon_interval, delay2, delay3)
                        print(f"                                                           ^^^ NEW BEST! ^^^")
        
        # Create the optimal canon
        if best_configuration:
            prolation, canon_interval, delay2, delay3 = best_configuration
            print(f"\nOptimal configuration found:")
            print(f"Prolation: {prolation} (Voice 2: {prolation}x, Voice 3: {prolation**2}x durations)")
            print(f"Canon interval: {canon_interval} (1=unison, 2=second, 3=third, etc.)")
            print(f"Voice 1: Original melody")
            print(f"Voice 2: Entry delay {delay2}, {prolation}x durations, transposed down by {canon_interval - 1} scale degrees")
            print(f"Voice 3: Entry delay {delay3}, {prolation**2}x durations, transposed down by {2 * (canon_interval - 1)} scale degrees")
            print(f"Key: {self.key}")
            print(f"Consonance score: {best_score:.3f}")
            
            # Build final score with fresh copies
            max_delay_final = max(Fraction(0), delay2, delay3)
            voice1 = self.create_canon_voice(self.copy_melody_notes(), Fraction(0), 
                                           voice_number=1, voice_name="Voice 1",
                                           max_delay_used=max_delay_final,
                                           canon_interval=canon_interval,
                                           prolation=prolation)
            voice2 = self.create_canon_voice(self.copy_melody_notes(), delay2, 
                                           voice_number=2, voice_name="Voice 2",
                                           max_delay_used=max_delay_final,
                                           canon_interval=canon_interval,
                                           prolation=prolation)
            voice3 = self.create_canon_voice(self.copy_melody_notes(), delay3, 
                                           voice_number=3, voice_name="Voice 3",
                                           max_delay_used=max_delay_final,
                                           canon_interval=canon_interval,
                                           prolation=prolation)
            
            # Set appropriate clefs
            abjad.attach(abjad.Clef('treble'), voice1[0])
            abjad.attach(abjad.Clef('treble'), voice2[0])
            abjad.attach(abjad.Clef('bass'), voice3[0])
            
            # Add time signature to first voice
            abjad.attach(self.time_signature, voice1[0])
            
            # Create the final score
            final_score = abjad.Score([voice1, voice2, voice3], name="Three-Voice Prolation Canon")
            
            # Add analysis markup AFTER creating the final score
            self.add_analysis_markup_to_score(final_score)
            
            return final_score
        else:
            print("No valid canon configuration found!")
            return None

def save_score_to_file(score: abjad.Score, filename: str = "canon_output.ly") -> str:
    """
    Save an Abjad score to a LilyPond file with proper headers.
    
    Args:
        score: Abjad Score object to save
        filename: Name of the output file (should end with .ly)
        
    Returns:
        Full path to the saved file
    """
    import os
    
    # Ensure filename has .ly extension
    if not filename.endswith('.ly'):
        filename += '.ly'
    
    # Get the current working directory
    output_path = os.path.join(os.getcwd(), filename)
    
    # Generate LilyPond content with proper structure
    lilypond_content = f'''\\version "2.24.0"
\\language "english"

\\header {{
  title = "Three-Voice Canon"
  composer = "Generated by Abjad"
}}

{abjad.lilypond(score)}
'''
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(lilypond_content)
    
    return output_path

def create_sample_melody() -> abjad.Staff:
    """Create the complete Frère Jacques melody - a classic canon with clear phrase structure."""
    # Complete Frère Jacques (Brother John) - a traditional canon with varied rhythms
    # First half: Frère Jacques, Frère Jacques
    # Second half: Dormez-vous? Dormez-vous?
    # Third part: Sonnez les matines, Sonnez les matines  
    # Fourth part: Din dan don, Din dan don
    melody = abjad.Staff("c'4 d'4 e'4 c'4 c'4 d'4 e'4 c'4 e'4 f'4 g'2 e'4 f'4 g'2 g'8 a'8 g'8 f'8 e'4 c'4 g'8 a'8 g'8 f'8 e'4 c'4 c'4 g4 c'2 c'4 g4 c'2")
    print("Sample melody (Complete Frère Jacques):")
    for i, note in enumerate(melody):
        if isinstance(note, abjad.Note):
            print(f"  Note {i}: {note.written_pitch()}")
    return melody

# Example usage
if __name__ == "__main__":
    # Create sample inputs
    melody_staff = create_sample_melody()
    time_signature = abjad.TimeSignature((4, 4))
    beat_template = ['S', 'w', 'm', 'w']  # Strong, weak, medium, weak
    
    # Create a custom rubric that penalizes unisons heavily
    custom_rubric = Rubric(
        strong_beat_consonance=5.0,
        medium_beat_consonance=2.0, 
        weak_beat_consonance=1.0,
        strong_beat_unison_penalty=-3.0,  # Heavy penalty for unisons on strong beats
        medium_beat_unison_penalty=-1.5,
        weak_beat_unison_penalty=-0.5,
        strong_beat_dissonance_penalty=-2.0,  # Penalty for dissonance on strong beats
        medium_beat_dissonance_penalty=-0.5,
        weak_beat_dissonance_penalty=0.0,  # No penalty for weak beat dissonance
        overall_consonance_bonus=10.0
    )
    
    # Create judge with custom rubric
    judge = Judge(custom_rubric, beat_template, time_signature, debug=False)
    
    # Generate canon with optimal prolation, interval, and entry search
    generator = CanonGenerator(
        melody_staff, 
        time_signature, 
        beat_template, 
        key="c major",
        max_entry_delay_measures=2,  # Increase to 2 measures for more options
        debug=False,  # Disable debug for cleaner output
        add_analysis_markup=True,  # Add interval analysis to the score
        judge=judge,  # Use custom judge
        search_intervals=[1, 3, 4, 5, 6],  # Skip 2nd and 7th (often dissonant)
        entry_resolution="strong_beat",  # Only allow entries on strong beats
        search_prolations=[1, 2, 3]  # Search normal, double, and triple prolation
    )
    canon_score = generator.find_optimal_canon()
    
    if canon_score:
        # Display the result
        print("\nGenerated LilyPond:")
        print(abjad.lilypond(canon_score))
        
        # Save to file
        output_file = save_score_to_file(canon_score, "three_voice_canon.ly")
        print(f"\nScore saved to: {output_file}")
    else:
        print("Failed to generate canon.")