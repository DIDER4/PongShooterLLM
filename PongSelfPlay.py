"""
Pong self play game project. October 2024.
- Programming a Pong game using an LLM
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 10:30:23 2024

@author: sila
"""

import pygame
import random
import sys

# Initialize pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
BALL_SIZE = 20
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 20
PADDLE_SPEED = 7
COMPUTER_SPEED = 5  # Speed of paddle movement in computer mode

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Set up screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Single Player Pong with Computer Mode")

# Ball setup
ball_x = SCREEN_WIDTH // 2
ball_y = SCREEN_HEIGHT // 2
ball_dx = random.choice([-4, 4])  # Ball speed and direction
ball_dy = random.choice([-4, 4])

# Paddle setup
paddle_x = (SCREEN_WIDTH - PADDLE_WIDTH) // 2
paddle_y = SCREEN_HEIGHT - PADDLE_HEIGHT - 10

# Game clock
clock = pygame.time.Clock()

# Score
score = 0
font = pygame.font.Font(None, 36)

# Control mode
computer_control = False

# Main game loop
def main():
    global ball_x, ball_y, ball_dx, ball_dy, paddle_x, score, computer_control

    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    print("Switch on-off selfplay")
                    computer_control = not computer_control  # Toggle computer control

        # Move paddle
        if not computer_control:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] and paddle_x > 0:
                paddle_x -= PADDLE_SPEED
            if keys[pygame.K_RIGHT] and paddle_x < SCREEN_WIDTH - PADDLE_WIDTH:
                paddle_x += PADDLE_SPEED
        else:
            # Computer control logic
            computer_move_paddle()

        # Move ball
        ball_x += ball_dx
        ball_y += ball_dy

        # Ball collision with wall
        if ball_x <= 0 or ball_x >= SCREEN_WIDTH - BALL_SIZE:
            ball_dx = -ball_dx
        if ball_y <= 0:
            ball_dy = -ball_dy
            score += 1  # Increase score when the ball hits the top wall

        # Ball collision with paddle
        if (paddle_y < ball_y + BALL_SIZE < paddle_y + PADDLE_HEIGHT and
                paddle_x < ball_x + BALL_SIZE / 2 < paddle_x + PADDLE_WIDTH):
            ball_dy = -ball_dy

        # Ball goes out of bounds (lose condition)
        if ball_y > SCREEN_HEIGHT:
            score = 0  # Reset score
            ball_x, ball_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2  # Reset ball position
            ball_dx, ball_dy = random.choice([-4, 4]), random.choice([-4, 4])

        # Drawing
        screen.fill(BLACK)  # Clear screen
        pygame.draw.rect(screen, WHITE, (paddle_x, paddle_y, PADDLE_WIDTH, PADDLE_HEIGHT))  # Paddle
        pygame.draw.ellipse(screen, WHITE, (ball_x, ball_y, BALL_SIZE, BALL_SIZE))  # Ball

        # Display score
        score_text = font.render("Score: " + str(score), True, WHITE)
        screen.blit(score_text, (10, 10))

        # Display control mode
        mode_text = font.render("Mode: " + ("Computer" if computer_control else "Player"), True, WHITE)
        screen.blit(mode_text, (10, 40))

        # Update display
        pygame.display.flip()
        clock.tick(60)  # 60 FPS

# Computer-controlled paddle movement
def computer_move_paddle():
    global paddle_x
    # Move paddle toward ball's x-position with some speed limit
    if paddle_x + PADDLE_WIDTH / 2 < ball_x:
        paddle_x += min(COMPUTER_SPEED, ball_x - (paddle_x + PADDLE_WIDTH / 2))
    elif paddle_x + PADDLE_WIDTH / 2 > ball_x:
        paddle_x -= min(COMPUTER_SPEED, (paddle_x + PADDLE_WIDTH / 2) - ball_x)

# Start game
if __name__ == "__main__":
    main()
