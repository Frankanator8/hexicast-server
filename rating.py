from glickoPlayer import GlickoPlayer
from database import glicko as glickoDB

def determineNewRating(rating,
                       rd,
                       volatility,
                       outcomes,
                       ratings,
                       rds,
                       multiplier=1):
    overallRc = 0
    overallRDc = 0
    overallVc = 0
    for i in range(len(outcomes)):
        thisPlayer = GlickoPlayer(rating=rating, rd=rd, vol=volatility)
        thisPlayer.update_player([ratings[i]], [rds[i]], [outcomes[i]])
        ratingChange = thisPlayer.rating - rating
        rdChange = thisPlayer.rd - rd
        volatilityChange = thisPlayer.vol - volatility

        overallRc += ratingChange
        overallRDc += rdChange
        overallVc += volatilityChange

    trueRatingChange = round(overallRc / len(outcomes))
    trueRDChange = round(overallRDc / len(outcomes))
    trueVolatilityChange = round(overallVc / len(outcomes))

    return trueRatingChange * multiplier, trueRDChange * multiplier, trueVolatilityChange * multiplier


def getRating(uuid):
    obj = glickoDB.find_data(uuid=uuid)
    return obj["rating"], obj["rd"], obj["vol"]

def changeRating(uuid, rating, rd, vol):
    glickoDB.updateInc("rating", rating, uuid=uuid)
    glickoDB.updateInc("rd", rd, uuid=uuid)
    glickoDB.updateInc("vol", vol, uuid=uuid)
