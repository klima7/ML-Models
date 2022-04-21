from itertools import cycle
import random
import sys

import pygame
from pygame.locals import *
import csv
import numpy as np

import argparse

# xCounter = 0
# velocityY = 0
FPS = 30
SCREENWIDTH  = 576
SCREENHEIGHT = 512
scrollingSpeed = 4
# amount by which base can maximum shift to left
PIPEGAPSIZE  = 100 # gap between upper and lower part of pipe
PIPEDISTANCE = SCREENWIDTH // 2
BASEY        = SCREENHEIGHT * 0.79
# image, sound and hitmask  dicts
IMAGES, SOUNDS, HITMASKS = {}, {}, {}



# list of all possible players (tuple of 3 positions of flap)
PLAYERS_LIST = (
    # red bird
    (
        'assets/sprites/redbird-downflap.png',
        'assets/sprites/redbird-midflap.png',
        'assets/sprites/redbird-upflap.png',
    ),
)

# list of backgrounds
BACKGROUNDS_LIST = (
    'assets/sprites/background-day_wide.png',
)

# list of pipes
PIPES_LIST = (
    'assets/sprites/pipe-green.png',
)


try:
    xrange
except NameError:
    xrange = range


#x 0-1600
#y 0-270
#n - stopień wielomianu
#x_max - maksimum na x
#y_max - maksimum na y  
def generatePointsForPipesPolynomial(seed, x, n=20, x_max=10, y_max=250):
    n=n-2
    # seed = 21827
    random.seed(seed)
    result=x[:]*(x[:]-x_max)
    step=x_max/n
    for i in np.arange(-step, x_max+step, step):
        mn=random.uniform(i, i+step)
        #print(mn)
        result=result*(x[:]-mn)
    
    result-=min(result)
    result/=max(result)
    result*=y_max
    return result

gameXRange = np.arange(0, 1600*4, 1)
generatedPolynomialPoints = np.zeros(1)



def main(inputFilePath, outputFilePath, difficultyLevel, gameSpeed, gameSeed, isInvulnerable=False):
    
    global generatedPolynomialPoints
    if gameSeed is None:
        gameSeed = 21827
    generatedPolynomialPoints = generatePointsForPipesPolynomial(seed=gameSeed, x=gameXRange, n=12, x_max=np.max(gameXRange))

    global SCREEN, FPSCLOCK
    global scrollingSpeed
    global PIPEGAPSIZE
    if gameSpeed is not None:
        scrollingSpeed = max(1, min(gameSpeed, 10))

    if difficultyLevel is not None:
        PIPEGAPSIZE = PIPEGAPSIZE - max(-50, min(difficultyLevel, 50))
    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    SCREEN = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
    pygame.display.set_caption('Flappy Bird')

    # numbers sprites for score display
    IMAGES['numbers'] = (
        pygame.image.load('assets/sprites/0.png').convert_alpha(),
        pygame.image.load('assets/sprites/1.png').convert_alpha(),
        pygame.image.load('assets/sprites/2.png').convert_alpha(),
        pygame.image.load('assets/sprites/3.png').convert_alpha(),
        pygame.image.load('assets/sprites/4.png').convert_alpha(),
        pygame.image.load('assets/sprites/5.png').convert_alpha(),
        pygame.image.load('assets/sprites/6.png').convert_alpha(),
        pygame.image.load('assets/sprites/7.png').convert_alpha(),
        pygame.image.load('assets/sprites/8.png').convert_alpha(),
        pygame.image.load('assets/sprites/9.png').convert_alpha()
    )

    # game over sprite
    # message sprite for welcome screen
    IMAGES['message'] = pygame.image.load('assets/sprites/message.png').convert_alpha()
    # base (ground) sprite
    IMAGES['base'] = pygame.image.load('assets/sprites/base_wide.png').convert_alpha()

    # sounds
    if 'win' in sys.platform:
        soundExt = '.wav'
    else:
        soundExt = '.ogg'

    SOUNDS['die']    = pygame.mixer.Sound('assets/audio/die' + soundExt)
    SOUNDS['hit']    = pygame.mixer.Sound('assets/audio/hit' + soundExt)
    SOUNDS['point']  = pygame.mixer.Sound('assets/audio/point' + soundExt)

    while True:
        # select background sprite
        bgIdx = 0 
        IMAGES['background'] = pygame.image.load(BACKGROUNDS_LIST[bgIdx]).convert()

        # select player sprite
        playerIdx = 0 
        IMAGES['player'] = (
            pygame.image.load(PLAYERS_LIST[playerIdx][0]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[playerIdx][1]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[playerIdx][2]).convert_alpha(),
        )

        # select random sprites
        pipeindex = 0 
        IMAGES['pipe'] = (
            pygame.transform.rotate(
                pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(), 180),
            pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(),
        )

        # hitmask for pipes
        HITMASKS['pipe'] = (
            getHitmask(IMAGES['pipe'][0]),
            getHitmask(IMAGES['pipe'][1]),
        )

        # hitmask for player
        HITMASKS['player'] = (
            getHitmask(IMAGES['player'][0]),
            getHitmask(IMAGES['player'][1]),
            getHitmask(IMAGES['player'][2]),
        )

        movementInfo = showWelcomeAnimation()
        crashInfo = mainGame(movementInfo, inputFilePath, outputFilePath, isInvulnerable)
        showGameOverScreen(crashInfo)

def convertRealPosToLogical(realPos):
    realMin = 330
    realMax = 60
    logicalMin = 0
    logicalMax = 250
    return translate(realPos, realMin, realMax, logicalMin, logicalMax)

def convertLogicalPosToReal(logicalPos):
    realMin = 330
    realMax = 60
    logicalMin = 0
    logicalMax = 250
    return translate(logicalPos, logicalMin, logicalMax, realMin, realMax, )

def translate(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

def showWelcomeAnimation():
    """Shows welcome screen animation of flappy bird"""
    # index of player to blit on screen
    playerIndex = 0
    playerIndexGen = cycle([0])


    playerx = int(SCREENWIDTH * 0.2)
    playery = int((SCREENHEIGHT - IMAGES['player'][1].get_height()) / 2)

    messagex = int((SCREENWIDTH - IMAGES['message'].get_width()) / 2)
    messagey = int(SCREENHEIGHT * 0.12)

    basex = 0
    # amount by which base can maximum shift to left
    baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()


    while True:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit(0)
            if event.type == KEYDOWN and (event.key == K_SPACE):
                return {
                    'playery': playery, # + playerShmVals['val'],
                    'basex': basex,
                    'playerIndexGen': playerIndexGen,
                }

        
        playerIndex = 0
        basex = -((-basex + 4) % baseShift)


        # draw sprites
        SCREEN.blit(IMAGES['background'], (0,0))
        SCREEN.blit(IMAGES['player'][playerIndex],
                    (playerx, playery)) # + playerShmVals['val']))
        SCREEN.blit(IMAGES['message'], (messagex, messagey))
        SCREEN.blit(IMAGES['base'], (basex, BASEY))

        pygame.display.update()
        FPSCLOCK.tick(FPS)


def mainGame(movementInfo, replayFile, outputFile, isInvulnerable=False):
    invulnerable = isInvulnerable
    score = playerIndex = 0
    xCounter = 0
    velocityY = 0
    pointList = []
    playerIndexGen = movementInfo['playerIndexGen']
    playerx, playery = int(SCREENWIDTH * 0.2), movementInfo['playery']
    
    autoplay = False
    autoplayPoints = []
    if replayFile is not None:
        autoplay = True
        with open(replayFile, 'r') as inFile:
            reader = csv.reader(inFile)
            autoplayPoints = list(reader)
            autoplayPoints = [tuple(np.array(x, dtype=(float, float))) for x in autoplayPoints]

    basex = movementInfo['basex']
    baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()

    # get 2 new pipes to add to upperPipes lowerPipes list
    pipe1RealXPos = (SCREENWIDTH + 10)
    pipe1LogicalXPos = xCounter + (pipe1RealXPos - playerx )
    newPolyPipe1 = getPolynomialPipe(pipe1LogicalXPos, pipe1RealXPos,  generatedPolynomialPoints)

    pipe2RealXPos = (SCREENWIDTH + 10 + (SCREENWIDTH // 2))
    pipe2LogicalXPos = xCounter + (pipe2RealXPos - playerx)
    newPolyPipe2 = getPolynomialPipe(pipe2LogicalXPos, pipe2RealXPos, generatedPolynomialPoints)
    
    newPipe1 = newPolyPipe1
    newPipe2 = newPolyPipe2

    # list of upper pipes
    upperPipes = [
        {'x': pipe1RealXPos, 'y': newPipe1[0]['y']},
        {'x': pipe2RealXPos, 'y': newPipe2[0]['y']},
    ]

    # list of lowerpipe
    lowerPipes = [
        {'x': pipe1RealXPos, 'y': newPipe1[1]['y']},
        {'x': pipe2RealXPos, 'y': newPipe2[1]['y']},
    ]

    # pipeVelX = -4
    pipeVelX = -1*scrollingSpeed
    playerRot = 0   # player's rotation

    holdingSpace = False
    singlePointMode = True

    while True:
        savePoint = False
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            playery -= 3
            velocityY = 1

        elif keys[pygame.K_DOWN]:
            playery += 3
            velocityY = -1
        else:
            velocityY = 0
        
        if xCounter > 50 and keys[pygame.K_SPACE]:
            if not singlePointMode or not holdingSpace:
                savePoint = True
            holdingSpace = True
        else:
            savePoint = False
            holdingSpace = False

        playerImageIndex = velocityY + 1

        playerMidYPos = playery + IMAGES['player'][playerImageIndex].get_height() / 2

        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit(0)
            if event.type == KEYDOWN and (event.key == K_SPACE):
                pass

            if event.type == KEYDOWN and (event.key == K_s):
                if outputFile is not None and autoplay == False:
                    filePath = outputFile
                    with open(filePath, 'a+', newline='') as outFile:
                        wr = csv.writer(outFile, csv.QUOTE_NONNUMERIC)
                        wr.writerows(pointList)
                    print('Position data saved to file')
                else:
                    print('Cannot save position data')
        
        if autoplay == True:
            if xCounter >= len(autoplayPoints):
                print('Game ends - no more autplay points')
                return {
                'y': playery,
                'groundCrash': False,
                'basex': basex,
                'upperPipes': upperPipes,
                'lowerPipes': lowerPipes,
                'score': score,
                'playerRot': playerRot
            }
            else:
                if (xCounter) < pipe1RealXPos - playerx - IMAGES['pipe'][0].get_width()*2:
                    playery = convertLogicalPosToReal(100)
                else:
                    logicalPos = autoplayPoints[xCounter][1]
                    realPos = convertLogicalPosToReal(logicalPos) - IMAGES['player'][playerImageIndex].get_height() / 2
                    playery = realPos

        if savePoint == True:
            if autoplay == False:
                playerMidYPos = playery + IMAGES['player'][playerImageIndex].get_height() / 2
                pointList.append((xCounter, convertRealPosToLogical(playerMidYPos)))
                print("saving position data " + str(len(pointList)))


        # check for crash here
        if (invulnerable == False):
            crashTest = checkCrash({'x': playerx, 'y': playery, 'index': playerImageIndex},
                                upperPipes, lowerPipes)
            if crashTest[0]:
                return {
                    'y': playery,
                    'groundCrash': crashTest[1],
                    'basex': basex,
                    'upperPipes': upperPipes,
                    'lowerPipes': lowerPipes,
                    'score': score,
                    'playerRot': playerRot
                }

        # check for score
        playerMidPos = playerx + IMAGES['player'][playerImageIndex].get_width() / 2

        for pipe in upperPipes:
            pipeMidPos = pipe['x'] + IMAGES['pipe'][0].get_width() / 2
            if pipeMidPos <= playerMidPos < pipeMidPos + 4:
                score += 1
                SOUNDS['point'].play()

        playerHeight = IMAGES['player'][playerImageIndex].get_height()

        # move pipes to left
        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            uPipe['x'] += pipeVelX
            lPipe['x'] += pipeVelX

        # add new pipe when first pipe is about to touch left of screen
        if 0 < upperPipes[0]['x'] < (-1*pipeVelX)+1:
            # newPipe = getRandomPipe()
            
            newPipeRealXPos = (SCREENWIDTH + 10)
            newPipeLogicalXPos = xCounter + (newPipeRealXPos - playerx )
            newPipe = getPolynomialPipe(newPipeLogicalXPos,newPipeRealXPos, generatedPolynomialPoints)
            upperPipes.append(newPipe[0])
            lowerPipes.append(newPipe[1])

        # remove first pipe if its out of the screen
        if upperPipes[0]['x'] < -IMAGES['pipe'][0].get_width():
            upperPipes.pop(0)
            lowerPipes.pop(0)

        # draw sprites
        SCREEN.blit(IMAGES['background'], (0,0))

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            SCREEN.blit(IMAGES['pipe'][0], (uPipe['x'], uPipe['y']))
            SCREEN.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

        SCREEN.blit(IMAGES['base'], (basex, BASEY))
        # print score so player overlaps the score
        showScore(score)

        visibleRot = playerRot
        playerSurface = pygame.transform.rotate(IMAGES['player'][playerImageIndex], visibleRot)
        SCREEN.blit(playerSurface, (playerx, playery))

        pygame.display.update()
        FPSCLOCK.tick(FPS)
        
        xCounter+= -1*pipeVelX
        
        # Do not go too far
        if xCounter >= np.max(gameXRange) - SCREENWIDTH:
            if autoplay == False:
                print('Game ends now - autosaving')
                with open('last_autosave.csv', 'w+', newline='') as outFile:
                        wr = csv.writer(outFile, csv.QUOTE_NONNUMERIC)
                        wr.writerows(pointList) 
            return {
                'y': playery,
                'groundCrash': False,
                'basex': basex,
                'upperPipes': upperPipes,
                'lowerPipes': lowerPipes,
                'score': score,
                'playerRot': playerRot
            }



def showGameOverScreen(crashInfo):
    """crashes the player down"""
    score = crashInfo['score']
    playerx = SCREENWIDTH * 0.2
    playery = crashInfo['y']
    playerHeight = IMAGES['player'][1].get_height()
    playerAccY = 2
    playerRot = crashInfo['playerRot']
    playerVelRot = 7

    basex = crashInfo['basex']

    upperPipes, lowerPipes = crashInfo['upperPipes'], crashInfo['lowerPipes']

    # play hit and die sounds
    SOUNDS['hit'].play()
    if not crashInfo['groundCrash']:
        SOUNDS['die'].play()

    while True:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pygame.quit()
                sys.exit(0)
            if event.type == KEYDOWN and (event.key == K_SPACE):
                xCounter = 0
                return

        # rotate only when it's a pipe crash
        if not crashInfo['groundCrash']:
            if playerRot > -90:
                playerRot -= playerVelRot

        # draw sprites
        SCREEN.blit(IMAGES['background'], (0,0))

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            SCREEN.blit(IMAGES['pipe'][0], (uPipe['x'], uPipe['y']))
            SCREEN.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

        SCREEN.blit(IMAGES['base'], (basex, BASEY))
        showScore(score)

        playerSurface = pygame.transform.rotate(IMAGES['player'][1], playerRot)
        SCREEN.blit(playerSurface, (playerx,playery))

        FPSCLOCK.tick(FPS)
        pygame.display.update()

def getRandomPipe():
    pipeMinPos = 60
    pipeMaxPos = 330
    pipeMidMinPos = pipeMinPos

    pipeMiddlePos = random.randrange(pipeMinPos+PIPEGAPSIZE//2, pipeMaxPos-PIPEGAPSIZE//2)

    gapY = pipeMiddlePos - PIPEGAPSIZE//2
    pipeHeight = IMAGES['pipe'][0].get_height()
    pipeX = SCREENWIDTH + 10

    return [
        {'x': pipeX, 'y': gapY - pipeHeight},  # upper pipe
        {'x': pipeX, 'y': gapY + PIPEGAPSIZE}, # lower pipe
    ]

def getPolynomialPipe(logicalPosition, realScreenPosition, polynomialPoints):
    pipeMiddlePos = polynomialPoints[logicalPosition]
    pipeMiddlePos = convertLogicalPosToReal(pipeMiddlePos)

    gapY = pipeMiddlePos - PIPEGAPSIZE//2
    pipeHeight = IMAGES['pipe'][0].get_height()
    pipeX = realScreenPosition

    return [
        {'x': pipeX, 'y': gapY - pipeHeight},  # upper pipe
        {'x': pipeX, 'y': gapY + PIPEGAPSIZE}, # lower pipe
    ]



def showScore(score):
    """displays score in center of screen"""
    scoreDigits = [int(x) for x in list(str(score))]
    totalWidth = 0 # total width of all numbers to be printed

    for digit in scoreDigits:
        totalWidth += IMAGES['numbers'][digit].get_width()

    Xoffset = (SCREENWIDTH - totalWidth) / 2

    for digit in scoreDigits:
        SCREEN.blit(IMAGES['numbers'][digit], (Xoffset, SCREENHEIGHT * 0.1))
        Xoffset += IMAGES['numbers'][digit].get_width()


def checkCrash(player, upperPipes, lowerPipes):
    """returns True if player collides with base or pipes."""
    pi = player['index']
    player['w'] = IMAGES['player'][pi].get_width()
    player['h'] = IMAGES['player'][pi].get_height()

    # if player crashes into ground
    if player['y'] + player['h'] >= BASEY - 1:
        return [True, True]
    # if player crashes into ceiling
    elif player['y'] <= 0:
        return [True, True]
    else:

        playerRect = pygame.Rect(player['x'], player['y'],
                      player['w'], player['h'])
        pipeW = IMAGES['pipe'][0].get_width()
        pipeH = IMAGES['pipe'][0].get_height()

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            # upper and lower pipe rects
            uPipeRect = pygame.Rect(uPipe['x'], uPipe['y'], pipeW, pipeH)
            lPipeRect = pygame.Rect(lPipe['x'], lPipe['y'], pipeW, pipeH)

            # player and upper/lower pipe hitmasks
            pHitMask = HITMASKS['player'][pi]
            uHitmask = HITMASKS['pipe'][0]
            lHitmask = HITMASKS['pipe'][1]

            # if bird collided with upipe or lpipe
            uCollide = pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask)
            lCollide = pixelCollision(playerRect, lPipeRect, pHitMask, lHitmask)

            if uCollide or lCollide:
                return [True, False]

    return [False, False]

def pixelCollision(rect1, rect2, hitmask1, hitmask2):
    """Checks if two objects collide and not just their rects"""
    rect = rect1.clip(rect2)

    if rect.width == 0 or rect.height == 0:
        return False

    x1, y1 = rect.x - rect1.x, rect.y - rect1.y
    x2, y2 = rect.x - rect2.x, rect.y - rect2.y

    for x in xrange(rect.width):
        for y in xrange(rect.height):
            if hitmask1[x1+x][y1+y] and hitmask2[x2+x][y2+y]:
                return True
    return False

def getHitmask(image):
    """returns a hitmask using an image's alpha."""
    mask = []
    for x in xrange(image.get_width()):
        mask.append([])
        for y in xrange(image.get_height()):
            mask[x].append(bool(image.get_at((x,y))[3]))
    return mask

if __name__ == '__main__':
    inFile = None
    outFile = None
    parser = argparse.ArgumentParser(description='Flappy bird simplified - predicting using regression')
    parser.add_argument('-o', '--outfile', action='store', dest='outfile', help='file for writing gathered positions', type=str)
    parser.add_argument('-i', '--infile', action='store', dest='infile', help='file with bird positions for replay', type=str)
    parser.add_argument('--difficulty', action='store', dest='difficulty', help='Set difficulty level (-50, 50), default 0', type=int)
    parser.add_argument('--speed', action='store', dest='speed', help='Set game speed (1-10), default = 4', type=int)
    parser.add_argument('--seed', action='store', dest='seed', help='Set seed for generating level', type=int)
    parser.add_argument('--IDDQD', help='Invulnerability', action='store_true')    
    
    args = parser.parse_args()
    main(args.infile, args.outfile, args.difficulty, gameSpeed=args.speed, gameSeed=args.seed, isInvulnerable=args.IDDQD)
