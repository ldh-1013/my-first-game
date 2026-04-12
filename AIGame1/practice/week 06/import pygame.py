import pygame

# Initialize Pygame
pygame.init()

# Define some colors (RGB values)
MINT_GREEN = (152, 255, 152)  # Bright mint green
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Game constants
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 400
CELL_SIZE = 20  # Size of each segment of the snake and other objects

# Function to draw a rectangle with a border
def draw_rect_with_border(surface, color, border_color, rect):
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, border_color, rect, 2)

# Set up the screen (just a plain black background for now)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
screen.fill(BLACK)

# Create the snake sprites
snake_images = {}

# Movement directions (key: (dx, dy), value: direction name)
directions = {
    (CELL_SIZE, 0): "right",
    (-CELL_SIZE, 0): "left",
    (0, -CELL_SIZE): "up",
    (0, CELL_SIZE): "down",
    (CELL_SIZE, -CELL_SIZE): "diagonal_up_right",
    (-CELL_SIZE, -CELL_SIZE): "diagonal_up_left",
    (CELL_SIZE, CELL_SIZE): "diagonal_down_right",
    (-CELL_SIZE, CELL_SIZE): "diagonal_down_left"
}

# Generate snake body images for each direction
for direction, name in directions.items():
    image = pygame.Surface((CELL_SIZE, CELL_SIZE))
    # Fill the body piece with mint green
    draw_rect_with_border(image, MINT_GREEN, BLACK, (0, 0, CELL_SIZE, CELL_SIZE))
    # Optional: Draw eyes for the snake head (pointing in the direction of movement)
    eye_radius = 2
    if name == "right":
        pygame.draw.circle(image, BLACK, (CELL_SIZE - 5, 8), eye_radius)
        pygame.draw.circle(image, BLACK, (CELL_SIZE - 5, 12), eye_radius)
    elif name == "left":
        pygame.draw.circle(image, BLACK, (5, 8), eye_radius)
        pygame.draw.circle(image, BLACK, (5, 12), eye_radius)
    # Add similar logic to position eyes for other directions...
    snake_images[name] = image

# Create the death state (collision) sprite
image_died = pygame.Surface((CELL_SIZE, CELL_SIZE))
draw_rect_with_border(image_died, MINT_GREEN, BLACK, (0, 0, CELL_SIZE, CELL_SIZE))
# Add an "X" or "😵" mark to indicate the snake is dead
pygame.draw.line(image_died, RED, (5, 5), (CELL_SIZE - 5, CELL_SIZE - 5), 3)
pygame.draw.line(image_died, RED, (5, CELL_SIZE - 5), (CELL_SIZE - 5, 5), 3)
snake_images["died"] = image_died

# --- Game loop components ---

# Snake state variables
snake_pos = [[100, 100], [100, 120], [100, 140]]  # List of coordinates (snake body)
snake_direction = "up"  # Current direction
game_over = False

# Function to draw the snake on the screen
def draw_snake(surface, snake_body, direction, game_state):
    # Iterate through each segment of the snake body
    for i, segment in enumerate(snake_body):
        x, y = segment
        # Use the regular body image for most segments
        if not game_state or (game_state and i > 0):
             surface.blit(snake_images[direction], (x, y))
        # Use the special 'died' image for the head segment if game_over is True
        elif game_state and i == 0:
             surface.blit(snake_images["died"], (x, y))

# Game loop
running = True
clock = pygame.time.Clock()
while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # Add logic to handle arrow key inputs to change snake_direction

    # Game logic: Update snake position, check for collisions
    if not game_over:
        # Move the snake based on the current snake_direction
        pass

    # Drawing and rendering
    screen.fill(BLACK)  # Clear the screen

    # Draw the snake based on its current position and game state
    draw_snake(screen, snake_pos, snake_direction, game_over)

    # Display a 'Game Over' message if appropriate
    if game_over:
        font = pygame.font.Font(None, 40)
        game_over_text = font.render("GAME OVER", True, WHITE)
        screen.blit(game_over_text, (100, 180))

    pygame.display.flip()  # Update the full display surface to the screen
    clock.tick(10)  # Adjust the frame rate (controlling the snake speed)

pygame.quit()