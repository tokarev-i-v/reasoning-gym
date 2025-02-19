import random
from dataclasses import dataclass
from enum import StrEnum
from itertools import count
from typing import List, Optional, Set, Tuple

from ..factory import ProceduralDataset, register_dataset


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class Relationship(StrEnum):
    MOTHER = "mother"
    FATHER = "father"
    SISTER = "sister"
    BROTHER = "brother"
    DAUGHTER = "daughter"
    SON = "son"
    WIFE = "wife"
    HUSBAND = "husband"
    GRANDMOTHER = "grandmother"
    GRANDFATHER = "grandfather"


@dataclass
class Person:
    name: str
    gender: Gender
    id: int
    spouse: Optional["Person"] = None
    parents: List["Person"] = None
    children: List["Person"] = None

    def __post_init__(self):
        self.parents = self.parents or []
        self.children = self.children or []

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        if not isinstance(other, Person):
            return False
        return self.id == other.id

    def add_child(self, child: "Person"):
        if child not in self.children:
            self.children.append(child)
        if self not in child.parents:
            child.parents.append(self)

    def add_spouse(self, spouse: "Person"):
        self.spouse = spouse
        spouse.spouse = self


@dataclass
class FamilyRelationshipsConfig:
    """Configuration for family relationship task generation"""

    min_family_size: int = 4
    max_family_size: int = 8
    male_names: List[str] = None
    female_names: List[str] = None
    seed: Optional[int] = None
    size: int = 500

    def __post_init__(self):
        # Default name lists if none provided
        default_male_names = [
            "James",
            "John",
            "Robert",
            "Michael",
            "William",
            "David",
            "Richard",
            "Joseph",
            "Thomas",
            "Charles",
            "Peter",
            "Daniel",
            "Matthew",
            "Christopher",
            "Andrew",
            "George",
            "Edward",
            "Benjamin",
            "Henry",
            "Samuel",
            "Alexander",
            "Oliver",
            "Jack",
            "Harry",
            "Jacob",
            "Noah",
            "Ethan",
            "Lucas",
            "Mason",
            "Logan",
            "Sebastian",
            "Theodore",
            "Owen",
            "Liam",
            "Aiden",
            "Kai",
            "Jayden",
            "Zion",
            "Phoenix",
            "Atlas",
            "Axel",
            "Ryder",
            "Finn",
        ]
        default_female_names = [
            "Mary",
            "Patricia",
            "Jennifer",
            "Linda",
            "Elizabeth",
            "Barbara",
            "Susan",
            "Jessica",
            "Sarah",
            "Karen",
            "Emma",
            "Lisa",
            "Anna",
            "Margaret",
            "Victoria",
            "Charlotte",
            "Sophia",
            "Isabella",
            "Olivia",
            "Ava",
            "Mia",
            "Emily",
            "Abigail",
            "Amelia",
            "Eleanor",
            "Grace",
            "Alice",
            "Lucy",
            "Chloe",
            "Sophie",
            "Lily",
            "Hannah",
            "Zoe",
            "Luna",
            "Nova",
            "Aria",
            "Willow",
            "Aurora",
            "Sage",
            "River",
            "Winter",
            "Sky",
            "Rain",
        ]

        if self.male_names is None:
            self.male_names = default_male_names
        if self.female_names is None:
            self.female_names = default_female_names

    def validate(self) -> None:
        """Validate configuration parameters"""
        assert self.min_family_size >= 3, "min_family_size must be at least 3"
        assert self.max_family_size >= self.min_family_size, "max_family_size must be >= min_family_size"
        assert len(self.male_names) > 0, "must provide male names"
        assert len(self.female_names) > 0, "must provide female names"


class FamilyRelationshipsDataset(ProceduralDataset):
    """Generates family relationship reasoning tasks"""

    def __init__(self, config: FamilyRelationshipsConfig):
        self._templates = [
            "What is {person1} to {person2}?",
            "How is {person1} related to {person2}?",
            "What relation is {person1} to {person2}?",
        ]
        super().__init__(config=config, seed=config.seed, size=config.size)

    def __getitem__(self, idx: int) -> dict:
        rng = random.Random(self.seed + idx)

        # Generate family tree
        family = self._generate_family(rng)

        # Select two people and their relationship
        person1, person2, relationship = self._get_relationship_question(rng, family)

        # Generate story describing the family relationships
        story = self._generate_story(family)

        # Format question
        question = rng.choice(self._templates).format(person1=person1.name, person2=person2.name)

        return {
            "question": f"{story}\n\n{question}",
            "answer": relationship.value,
            "metadata": {
                "person1": person1.name,
                "person2": person2.name,
                "relationship": relationship.value,
                "family_size": len(family),
            },
        }

    def _generate_family(self, rng: random.Random) -> Set[Person]:
        """Generate a random family tree"""
        family_size = rng.randint(self.config.min_family_size, self.config.max_family_size)
        family = set()
        used_names = set()

        def get_name(gender: Gender) -> str:
            names = self.config.male_names if gender == Gender.MALE else self.config.female_names
            available = [n for n in names if n not in used_names]
            if not available:
                return None
            name = rng.choice(available)
            used_names.add(name)
            return name

        # Create ID counter
        id_counter = count()

        # Create grandparents generation
        grandfather = Person(get_name(Gender.MALE), Gender.MALE, next(id_counter))
        grandmother = Person(get_name(Gender.FEMALE), Gender.FEMALE, next(id_counter))
        grandfather.add_spouse(grandmother)
        family.update([grandfather, grandmother])

        # Create parents
        father = Person(get_name(Gender.MALE), Gender.MALE, next(id_counter))
        mother = Person(get_name(Gender.FEMALE), Gender.FEMALE, next(id_counter))
        father.add_spouse(mother)
        grandfather.add_child(father)
        grandmother.add_child(father)
        family.update([father, mother])

        # Add children
        while len(family) < family_size:
            gender = rng.choice([Gender.MALE, Gender.FEMALE])
            name = get_name(gender)
            if not name:
                break
            child = Person(name, gender, next(id_counter))
            father.add_child(child)
            mother.add_child(child)
            family.add(child)

        return family

    def _get_relationship_question(
        self, rng: random.Random, family: Set[Person]
    ) -> Tuple[Person, Person, Relationship]:
        """Select two family members and determine their relationship"""
        person1, person2 = rng.sample(list(family), 2)

        # Determine relationship
        if person1 in person2.parents:
            relationship = Relationship.MOTHER if person1.gender == Gender.FEMALE else Relationship.FATHER
        elif person2 in person1.parents:
            relationship = Relationship.DAUGHTER if person1.gender == Gender.FEMALE else Relationship.SON
        elif person1.spouse == person2:
            relationship = Relationship.WIFE if person1.gender == Gender.FEMALE else Relationship.HUSBAND
        elif person1.parents and person2.parents and set(person1.parents) == set(person2.parents):
            relationship = Relationship.SISTER if person1.gender == Gender.FEMALE else Relationship.BROTHER
        elif person1 in [p for parent in person2.parents for p in parent.parents]:
            relationship = Relationship.GRANDMOTHER if person1.gender == Gender.FEMALE else Relationship.GRANDFATHER
        else:
            # Try again with different people
            return self._get_relationship_question(rng, family)

        return person1, person2, relationship

    def _generate_story(self, family: Set[Person]) -> str:
        """Generate a story describing the family relationships"""
        story_parts = []

        # Find married couples
        couples = set()
        for person in family:
            if person.spouse and (person.spouse, person) not in couples:
                couples.add((person, person.spouse))

        # Describe marriages and children for each couple
        described_children = set()  # Track which children have been described
        for person1, person2 in couples:
            story_parts.append(f"{person1.name} is married to {person2.name}.")

            # Only describe children once per couple
            children = [c for c in person1.children if c not in described_children]
            if children:
                children_names = [c.name for c in children]
                described_children.update(children)  # Mark these children as described

                if len(children_names) == 1:
                    story_parts.append(f"They have a child called {children_names[0]}.")
                else:
                    *first, last = children_names
                    children_str = ", ".join(first) + f" and {last}"
                    story_parts.append(f"They have children called {children_str}.")

        return " ".join(story_parts)


register_dataset("family_relationships", FamilyRelationshipsDataset, FamilyRelationshipsConfig)
