export default function MovieCard({ movie, onSelect }) {
  return (
    <div 
      onClick={() => onSelect(movie)}
      className="group cursor-pointer bg-white dark:bg-gray-800 rounded-xl overflow-hidden border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-all flex flex-col"
    >
      <div className="relative aspect-[2/3] overflow-hidden bg-gray-100 dark:bg-gray-700">
        <img 
          src={movie.img} 
          alt={movie.title} 
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" 
        />
        
        {}
        {movie.category && (
          <span className="absolute top-2 left-2 px-2 py-0.5 bg-black/60 backdrop-blur-md text-white font-bold text-[10px] rounded-md uppercase tracking-wider">
            {movie.category}
          </span>
        )}

        {}
        <div className="absolute bottom-2 right-2 px-2 py-1 bg-yellow-500 text-gray-900 font-black text-xs rounded-lg shadow">
          ★ {movie.rating}
        </div>
      </div>
      
      <div className="p-3 flex flex-col flex-1 justify-between">
        <h3 className="font-bold text-sm text-gray-900 dark:text-white line-clamp-1 group-hover:text-yellow-600 dark:group-hover:text-yellow-400 transition-colors">
          {movie.title}
        </h3>
        <p className="text-xs text-gray-400 mt-1">{movie.year} • {movie.genre}</p>
      </div>
    </div>
  );
}