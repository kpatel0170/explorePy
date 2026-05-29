from turtle import Screen
import time

from snake import Snake
from food import Food
from scoreboard import ScoreBoard


def setup_screen():
    screen = Screen()
    screen.setup(600, 600)
    screen.bgcolor("black")
    screen.title("Snake Game")
    screen.tracer(0)
    return screen


def register_controls(screen, snake):
    screen.listen()
    screen.onkey(snake.up, "Up")
    screen.onkey(snake.down, "Down")
    screen.onkey(snake.left, "Left")
    screen.onkey(snake.right, "Right")


def main():
    screen = setup_screen()
    snake = Snake()
    food = Food()
    scoreboard = ScoreBoard()

    register_controls(screen, snake)

    game_is_on = True
    while game_is_on:
        screen.update()
        time.sleep(0.1)
        snake.move()

        if snake.head.distance(food) < 15:
            scoreboard.increase_score()
            snake.extend_length()
            food.refresh()

        if (
            snake.head.xcor() > 280
            or snake.head.xcor() < -280
            or snake.head.ycor() > 280
            or snake.head.ycor() < -280
        ):
            scoreboard.reset_scoreboard()
            snake.reset_snake()

        for segment in snake.segments[1:]:
            if snake.head.distance(segment) < 10:
                scoreboard.reset_scoreboard()
                snake.reset_snake()
                break

    screen.exitonclick()


if __name__ == "__main__":
    main()
