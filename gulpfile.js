const gulp = require("gulp");
const rename = require("gulp-rename");
const webpack = require("webpack-stream");

gulp.task('javascript', function() {
  return gulp
    .src("./preen_test/assets/js/webpack_entry.js")
    .pipe(webpack(require("./webpack.config.js")))
    .pipe(rename("main.js"))
    .pipe(gulp.dest("./preen_test/static/js/"));
});

gulp.task('watch-js', function(done) {
  gulp.watch(["./apps/preen_test/assets/js/**/*.js"], gulp.series("javascript"));
  done();
})



gulp.task('styles', function() {
  const postcss = require("gulp-postcss");
  const tailwindcss = require("tailwindcss");

  return gulp
    .src("./preen_test/assets/styles/tailwind_entry.css")
    .pipe(
      postcss([
        require("postcss-import"),
        require("postcss-preset-env"),
        tailwindcss("./tailwind.config.js"),
        require("autoprefixer"),
      ])
    )
    .pipe(rename("main.css"))
    .pipe(gulp.dest("./preen_test/static/css/"));
});

gulp.task('watch-css', function(done) {
  gulp.watch(
    [
      './apps/preen_test/**/*.css',
      './tailwind.config.js'
    ], gulp.series('styles')
  )
  done();
});




exports.default = gulp.series('styles', 'javascript', 'watch-css', 'watch-js');