const passport = require("passport");
const LocalStrategy = require("passport-local").Strategy;
const User = require("./db/models/User");

passport.use("local-signup", new LocalStrategy({
    passReqToCallback: true
}, function(req, username, password, done) {
    User.findOne({ username }, (err, user) => {
        if (err) {
            return done(err);
        }

        if (user) {
            return done(null, false);
        } else {
            const newUser = new User();
            newUser.username = username;
            newUser.password = password;

            newUser.save(err => {
                if (err) {
                    done(err);
                } else {
                    done(null, newUser);
                }
            })
        }
    })
}));

passport.use("local-login", new LocalStrategy(function(username, password, done) {
    User.findOne({ username }, (err, user) => {
        if (err) {
            return done(err);
        }

        if (!user) {
            return done(null, false);
        }

        if (!user.verifyPassword(password)) {
            return done(null, false);
        }

        return done(null, user);
    });
}));

passport.serializeUser((user, done) => {
    done(null, user.username);
});

passport.deserializeUser((username, done) => {
    User.findOne({ username }, (err, user) => {
        if (err) {
            return done(err);
        }

        done(null, user);
    });
});

module.exports = passport;
