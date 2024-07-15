import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())
    
    
    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for variable in self.crossword.variables:
            required_len = variable.length

            to_remove = []
            for word in self.domains[variable]:
                if len(word) != required_len:
                    to_remove.append(word)
            for word in to_remove:
                self.domains[variable].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        flag = False

        overlap = self.crossword.overlaps[x, y]
        if overlap is None:
            return flag

        to_remove = []

        for x_value in self.domains[x]:
            consistent = False
            for y_value in self.domains[y]:
                if x_value[overlap[0]] == y_value[overlap[1]]:
                    consistent = True
                    break  
            if not consistent:
                to_remove.append(x_value)
                flag = True  

        for value in to_remove:
            self.domains[x].remove(value)

        return flag

                    

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            queue =[]
            for x in self.crossword.variables:
                for y in self.crossword.neighbours(x):
                    queue.append((x , y))
        else:
            queue = arcs
            while queue:
                x, y = queue.pop(0)
                if self.revise(x, y):
                    if not self.domains[x]:
                        return False
                    for z in self.crossword.neighbors(x) - {y}:
                        queue.append((z, x))
    
        return True
    
    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        return all(var in assignment for var in self.variables)


    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        for var, value in assignment.items():
            for constraint in self.constraints.get(var, []):  # Handle cases where var might not have constraints
                other_var, expected_value = constraint
                if other_var in assignment and assignment[other_var] != expected_value:
                    return False  # Inconsistency found, return False

        return True
        
    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        conflict_counts = {value: 0 for value in self.domains[var]}

        for constraint in self.constraints.get(var, []):
            other_var, expected_value = constraint
            for value in self.domains[var]:
                if value != expected_value:
                    conflict_counts[value] += 1  

        return sorted(self.domains[var], key=conflict_counts.get)
    
    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned_vars = [var for var in csp.variables if var not in assignment]
        min_remaining_values = float('inf')
        result = None
        for var in unassigned_vars:
            remaining_values = len(csp.possible_values(var, assignment))
            if remaining_values < min_remaining_values:
                min_remaining_values = remaining_values
                result = var
            elif remaining_values == min_remaining_values:
                degree = len(csp.constraints[var])
                if degree > len(csp.constraints.get(result, [])):
                    result = var
        return result

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if is_complete(assignment, csp):
            return assignment
        var = select_unassigned_variable(csp, assignment)
        for value in csp.possible_values(var, assignment):
            if is_consistent(var, value, assignment, csp):
                assignment[var] = value
                inferences = {}
                if forward_check(var, value, assignment, csp, inferences):
                    result = backtrack(assignment, csp)
                    if result is not None:
                        return result
                del assignment[var]
                for k in inferences:
                    del assignment[k]
        return None

    def is_complete(assignment, csp):
        """
        Return True if the assignment is complete, False otherwise.
        """
        return set(assignment.keys()) == set(csp.variables)

    def is_consistent(var, value, assignment, csp):
        """
        Return True if the assignment is consistent, False otherwise.
        """
        for constraint in csp.constraints[var]:
            if not constraint(var, value, assignment):
                return False
        return True

    def forward_check(var, value, assignment, csp, inferences):
        """
        Perform forward checking and return True if the assignment is still
        consistent, False otherwise.
        """
        for constraint in csp.constraints[var]:
            for other_var in constraint.scope:
                if other_var!= var and other_var not in assignment:
                    for other_value in csp.possible_values(other_var, assignment):
                        if not constraint(other_var, other_value, assignment):
                            csp.possible_values(other_var, assignment).remove(other_value)
                            inferences[other_var] = other_value
                            if not csp.possible_values(other_var, assignment):
                                return False
        return True

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
